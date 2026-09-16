from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import ast
import hashlib
import re


SAFE_IMPORTS={
    "__future__": {"annotations"},
    "phoenix.autonomy.executor_adapters": {"AdapterExecutionResult","AdapterExecutionContext"},
    "typing": {"Any"},
}
FORBIDDEN_CALLS={
    "eval","exec","compile","open","input","__import__","breakpoint",
    "globals","locals","vars"
}
FORBIDDEN_NAMES={
    "os","subprocess","socket","ctypes","importlib","sys","pathlib",
    "shutil","tempfile","urllib","http","requests","multiprocessing"
}
FORBIDDEN_NODE_TYPES=(
    ast.With,ast.AsyncWith,ast.Global,ast.Nonlocal,ast.Lambda,
    ast.Yield,ast.YieldFrom,ast.Await,
)
if hasattr(ast,"TryStar"):
    FORBIDDEN_NODE_TYPES=FORBIDDEN_NODE_TYPES+(ast.TryStar,)


def _safe_module_name(adapter_id:str)->str:
    value=re.sub(r"[^A-Za-z0-9_]","_",adapter_id).strip("_")
    if not value:
        raise ValueError("adapter id cannot produce module name")
    if value[0].isdigit():
        value="adapter_"+value
    return value.lower()


def _literal(node:ast.AST):
    return ast.literal_eval(node)


@dataclass(frozen=True)
class AdapterImplementationValidation:
    status: str
    errors: tuple[str,...]
    adapter_id: str
    engine_id: str
    class_name: str
    module_path: str
    target_path: str
    source_sha256: str
    source: str

    @property
    def activation_ready(self)->bool:
        return self.status=="PASS" and not self.errors

    def contract(self)->dict[str,Any]:
        return {
            "adapter_id":self.adapter_id,
            "engine_id":self.engine_id,
            "class_name":self.class_name,
            "module_path":self.module_path,
            "target_path":self.target_path,
            "source_sha256":self.source_sha256,
            "status":self.status,
            "errors":list(self.errors),
            "activation_ready":self.activation_ready,
        }


class AdapterImplementationValidator:
    def __init__(self,policy:dict[str,Any]):
        self.policy=policy

    def validate(
        self,
        source:str,
        *,
        engine_id:str,
        descriptor:dict[str,Any],
    )->AdapterImplementationValidation:
        errors=[]
        adapter_id=str(descriptor["adapter_id"])
        expected_impl=str(descriptor.get("implementation") or "")
        expected_class=expected_impl.partition(":")[2] or None
        module_name=_safe_module_name(adapter_id)
        module_path=f"phoenix.autonomy.generated_adapters.{module_name}"
        target_path=f"phoenix/autonomy/generated_adapters/{module_name}.py"
        digest=hashlib.sha256(source.encode("utf-8")).hexdigest()

        try:
            tree=ast.parse(source,filename=target_path,mode="exec")
        except SyntaxError as exc:
            return AdapterImplementationValidation(
                "FAIL",(f"SYNTAX:{exc.msg}",),adapter_id,engine_id,
                expected_class or "",module_path,target_path,digest,source
            )

        classes=[]
        for node in tree.body:
            if isinstance(node,ast.ImportFrom):
                module=node.module or ""
                allowed=SAFE_IMPORTS.get(module)
                if allowed is None:
                    errors.append(f"TOPLEVEL_IMPORT_DENY:{module}")
                else:
                    for alias in node.names:
                        if alias.name not in allowed or alias.asname:
                            errors.append(f"TOPLEVEL_IMPORT_NAME_DENY:{module}:{alias.name}")
            elif isinstance(node,ast.ClassDef):
                classes.append(node)
            elif isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str):
                # module docstring only
                continue
            else:
                errors.append(f"TOPLEVEL_NODE_DENY:{type(node).__name__}")

        if len(classes)!=1:
            errors.append("EXACTLY_ONE_ADAPTER_CLASS_REQUIRED")
            class_node=classes[0] if classes else None
        else:
            class_node=classes[0]

        actual_class=class_node.name if class_node else (expected_class or "")
        if expected_class and actual_class!=expected_class:
            errors.append(f"CLASS_NAME_MISMATCH:{actual_class}:{expected_class}")

        values={}
        execute_found=False
        if class_node:
            if class_node.decorator_list:
                errors.append("CLASS_DECORATOR_DENY")
            if class_node.bases or class_node.keywords:
                errors.append("CLASS_INHERITANCE_DENY")

            for item in class_node.body:
                if isinstance(item,ast.Expr) and isinstance(item.value,ast.Constant) and isinstance(item.value.value,str):
                    continue
                if isinstance(item,ast.Assign):
                    if len(item.targets)!=1 or not isinstance(item.targets[0],ast.Name):
                        errors.append("CLASS_ASSIGN_TARGET_DENY")
                        continue
                    try:
                        values[item.targets[0].id]=_literal(item.value)
                    except Exception:
                        errors.append(f"CLASS_ASSIGN_NONLITERAL:{item.targets[0].id}")
                elif isinstance(item,ast.AnnAssign):
                    if not isinstance(item.target,ast.Name) or item.value is None:
                        errors.append("CLASS_ANNASSIGN_DENY")
                        continue
                    try:
                        values[item.target.id]=_literal(item.value)
                    except Exception:
                        errors.append(f"CLASS_ASSIGN_NONLITERAL:{item.target.id}")
                elif isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    if isinstance(item,ast.AsyncFunctionDef):
                        errors.append(f"ASYNC_METHOD_DENY:{item.name}")
                    if item.decorator_list:
                        errors.append(f"METHOD_DECORATOR_DENY:{item.name}")
                    if item.args.defaults or any(x is not None for x in item.args.kw_defaults):
                        errors.append(f"METHOD_DEFAULT_DENY:{item.name}")
                    if item.name=="execute":
                        execute_found=True
                else:
                    errors.append(f"CLASS_NODE_DENY:{type(item).__name__}")

        expected={
            "adapter_id":adapter_id,
            "engine_id":engine_id,
            "actions":tuple(str(x) for x in descriptor.get("actions",())),
            "mutation_capable":bool(descriptor.get("mutation_capable")),
            "gateway_required":bool(descriptor.get("gateway_required")),
        }
        for key,val in expected.items():
            actual=values.get(key,"__MISSING__")
            if key=="actions" and isinstance(actual,list):
                actual=tuple(actual)
            if actual!=val:
                errors.append(f"CONTRACT_VALUE_MISMATCH:{key}")
        if not execute_found:
            errors.append("EXECUTE_METHOD_REQUIRED")

        for node in ast.walk(tree):
            if isinstance(node,FORBIDDEN_NODE_TYPES):
                errors.append(f"AST_NODE_DENY:{type(node).__name__}")
            if isinstance(node,ast.Import):
                errors.append("IMPORT_DENY")
            if isinstance(node,ast.ImportFrom) and node not in tree.body:
                errors.append("NESTED_IMPORT_DENY")
            if isinstance(node,ast.Name) and node.id in FORBIDDEN_NAMES:
                errors.append(f"FORBIDDEN_NAME:{node.id}")
            if isinstance(node,ast.Attribute) and node.attr.startswith("__"):
                errors.append(f"DUNDER_ATTRIBUTE_DENY:{node.attr}")
            if isinstance(node,ast.Call):
                if isinstance(node.func,ast.Name) and node.func.id in FORBIDDEN_CALLS:
                    errors.append(f"FORBIDDEN_CALL:{node.func.id}")
                if isinstance(node.func,ast.Name) and node.func.id=="NotImplementedError":
                    errors.append("IMPLEMENTATION_INCOMPLETE")
            if isinstance(node,ast.Raise):
                exc=node.exc
                if isinstance(exc,ast.Call) and isinstance(exc.func,ast.Name) and exc.func.id=="NotImplementedError":
                    errors.append("IMPLEMENTATION_INCOMPLETE")
                if isinstance(exc,ast.Name) and exc.id=="NotImplementedError":
                    errors.append("IMPLEMENTATION_INCOMPLETE")

        errors=tuple(sorted(set(errors)))
        return AdapterImplementationValidation(
            "PASS" if not errors else "FAIL",errors,adapter_id,engine_id,
            actual_class,module_path,target_path,digest,source
        )

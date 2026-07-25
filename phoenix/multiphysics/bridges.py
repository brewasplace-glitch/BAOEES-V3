def publish_to_digital_twin(database,execution):
    workflow=database.create_object("multiphysics_workflow",execution["workflow_id"],
        properties={"success":execution["success"],"task_count":len(execution["executions"])})
    fusion=database.create_object("multiphysics_fusion",execution["workflow_id"]+" fusion",
        properties={"success":execution["success"],"metrics":execution["fusion"]["metrics"]})
    database.relate(fusion.object_id,"fuses",workflow.object_id)
    return {"workflow":workflow.object_id,"fusion":fusion.object_id}

def publish_to_knowledge_graph(graph,execution):
    workflow=graph.create_node(node_type="multiphysics_workflow",label=execution["workflow_id"],
        properties={"success":execution["success"],"task_count":len(execution["executions"])})
    fusion=graph.create_node(node_type="multiphysics_fusion",label=execution["workflow_id"]+" fusion",
        properties={"success":execution["success"],"metrics":execution["fusion"]["metrics"]})
    graph.connect(fusion.node_id,"fuses",workflow.node_id)
    return {"workflow":workflow.node_id,"fusion":fusion.node_id}

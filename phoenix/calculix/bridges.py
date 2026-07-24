from phoenix.database import ProjectDatabase
from phoenix.knowledge_graph import KnowledgeGraphEngine

def publish_to_digital_twin(database: ProjectDatabase, model, result):
    m = database.create_object("finite_element_model", model.name,
        properties={"model_id":model.model_id,"node_count":len(model.nodes),"element_count":len(model.beam_elements)})
    r = database.create_object("finite_element_analysis_result", f"{model.name} result",
        properties={"analysis_type":result.analysis_type,"runtime_mode":result.runtime_mode,"checksum_sha256":result.checksum_sha256})
    database.relate(r.object_id, "analyzes", m.object_id)
    return {"model":m.object_id,"result":r.object_id}

def publish_to_knowledge_graph(graph: KnowledgeGraphEngine, model, result):
    m = graph.create_node(node_type="finite_element_model", label=model.name,
        properties={"model_id":model.model_id,"element_count":len(model.beam_elements)})
    r = graph.create_node(node_type="finite_element_analysis_result", label=f"{model.name} result",
        properties={"analysis_type":result.analysis_type,"runtime_mode":result.runtime_mode,"checksum_sha256":result.checksum_sha256})
    graph.connect(r.node_id, "analyzes", m.node_id)
    return {"model":m.node_id,"result":r.node_id}

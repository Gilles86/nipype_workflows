def show_workflow(workflow):
    from IPython.display import Image
    import os
    workflow.write_graph()
    return Image(os.path.join(workflow.base_dir, workflow.name, 'graph.dot.png'))

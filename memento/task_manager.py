class TaskManager:
    def __init__(self, kg):
        self.kg = kg
        self.tasks = {}

    def parse_llm_response(self):
        # The LLM can specify a set of tasks that can include the following types:
        #
        # create entity
        # update entity
        # create action
        # update action
        # query (knowledge graph)
        # change hat 
        # call tool
        # query agent
        #
        # design note: while in principle the generic entity and relationship tasks can 
        # handle all knowledge graph updates, we preserve the integrity of the structural
        # entities by constraining operations on them and by making those special cases
        # prominant in the prompt instructions 
        #
        # 

        

    def execute_tasks(self):
        # executes the current tasks
        

    def record_task_results(self):
        # attaches the results to the episode as "result" entities and in some cases to the active Action

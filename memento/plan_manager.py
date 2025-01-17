class PlanManager:
    def __init__(self, kg):
        self.kg = kg

    def update_plan(self, episode.id):
        # get relevant SQL queries/templates and instructions for their use
        # get relevant relevant LLM prompt templates and instructions for their use.
        # find tasks that are marked as "in context"
        # find actions and their results associated with the current episode
        # analyze the tasks and actions to specfy a set of KG update operations to 
        # the actions: revise the status of existing actions, e.g. an action
        # progress may have changed, results need to be linked to it, it may 
        # have completed, etc.  New actions can be added and linked to other
        # actions. The overall design is that the agent's plans and much of 
        # its history are described by actions that are planned/in progress/completed
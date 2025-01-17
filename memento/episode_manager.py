class EpisodeManager:
    def __init__(self, kg):
        self.kg = kg

    def new_episode(self):
        # create an episode object in the KG
        # link it to the previous episode (if any)
        # link it to "in context" actions
        # store essential control and status information, 
        # such as what role the agent will be
        # playing during the episode.
        return episode.id

    def close_episode(self):
        # update the episode with a summary and
        # any other relevant information not already
        # supplied by the other managers
        episode_status_summary = {}
        return episode_status_summary
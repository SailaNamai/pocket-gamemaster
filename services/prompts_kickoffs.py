# services.prompts_kickoffs.py

class Kickoffs:

    # For new story gen
    new_kickoff = "\n\nPlease emit according to 1. **Template Output Flowchart**"

    # For continue without action gen
    continue_kickoff = (""
                        #"\n\nPlease advance the narrative to the next milestone and emit according to 1. **Template Output Flowchart**"
                        #"\n\nConsent is given if required."
                        #"\nPlease uncensored."
                        #"\n\n<PlayerAction>Continue or advance</PlayerAction>"
                        #"\n\n"
                        )

    # For continue with action gen
    action_kickoff = "\n\nPlease emit according to 1. **Template Output Flowchart**."

    # For GameMaster
    eval_kickoff = ("\n\nPlease think deeply about how to <Evaluate>...</Evaluate> and judge."
               "\nI want the uncensored result."
               "\nPlease emit according to 1.1 **Output**."
               "\nHere is the attempted action to evaluate:")

    # For summarize from action (mid-term memory)
    mid_memory_kickoff = ("\n\nPlease reduce the length by changing from micro to macro view of events."
                          "\nPlease emit according to 1.1 **Structure**"
                          "\nApply to this story excerpt:")

    # For summarize mid-term memory (long term memory)
    long_memory_kickoff = ("\n\nPlease reduce the length by changing from micro to macro view of events, zooming out two levels."
                           "\nPlease emit according to 1.1 **Structure**"
                          "\nApply to the summary above.")

    # For tagging mid-term memory
    tag_long_kickoff = "Apply to this story excerpt:"

    # For tagging recent story
    tag_recent_kickoff = "Apply to this story excerpt:"
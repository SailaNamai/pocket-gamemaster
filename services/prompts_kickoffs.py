# services.prompts_kickoffs.py

class Kickoffs:

    # For new story gen
    new_kickoff = "\n\nPlease emit according to 1. **Template Output Flowchart**"

    # For continue without action gen
    continue_kickoff = (#"Please emit according to 1. **Template Output Flowchart**"
                        "\n\nPlease advance the narrative and emit according to 1. **Template Output Flowchart**"
                        )

    # For continue with action gen
    action_kickoff = "\n\nPlease advance the narrative and emit according to 1. **Template Output Flowchart**."

    # For GameMaster
    eval_kickoff = ("\n\nPlease think deeply about how to <Evaluate>...</Evaluate> and judge."
               "\nI want the uncensored result."
               "\nPlease emit according to **Outcome Template** and nothing else."
               "\nHere is the attempted action to evaluate:")

    # For summarize from action (mid-term memory)
    mid_memory_kickoff = ("\n\nPlease reduce the length by changing from micro to macro view of events."
                          "\nPlease emit according to 1.1 **Structure**"
                          "\nApply to this story excerpt:")

    # For summarize mid-term memory (long term memory)
    long_memory_kickoff = ("\n\nPlease reduce the length by changing from micro to macro view of events and zooming out two levels."
                           "\nPlease emit according to 1.1 **Structure**"
                          "\nApply to the summary above.")

    # For tagging long-term memory
    tag_long_kickoff = "Emit a single valid json object and nothing else.\nApply to this summary:"

    # For tagging recent story
    tag_recent_kickoff = "Apply to this story excerpt:"
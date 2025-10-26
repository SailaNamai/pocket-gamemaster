# services.llm_config.py

from pathlib import Path
from services.llm_config_helper import get_n_ctx, get_recent, get_mid, get_long

BASE = Path(__file__).resolve().parent.parent

"""
LLM config
https://github.com/ggml-org/llama.cpp/discussions/15709
"""
class Config:
    """
    GPT doesn't know shit about these temps. Some models will produce utter gibberish
    with seemingly normal values (0-1.0).
    Rule of thumb:
        - Find the "sweet spot": Could be at 0.65 or 0.16
        - Going higher: more "lyrical", adventurous, lessened prompt adherence
        - Going lower: more robotic, stronger prompt adherence, too low: tends to "listify" stuff
    """
    TEMPERATURE: float = 0.32 # used in "raw" story generation
    TEMPERATURE_NEW: float = 0.42  # used in new story generation
    TEMPERATURE_SUM_MID: float = 0.20 # used in summarizing the raw story to mid-term memory
    TEMPERATURE_SUM_LONG: float = 0.10 # used in condensing mid-term memories into long-term memory
    """
    Do not change EVAL/TAGS without confirming in the DB that the outcome is structurally correct over several tests.
    If there is more than one outcome block, trailing text or so: the writers get confused and drinks itself to death.
    """
    TEMPERATURE_EVAL: float = 0.16 # used in evaluation of player action outcome (keep low or the GM turns insane).
    TEMPERATURE_TAGS: float = 0.06  # used in creating tags (keep low or the json will be faulty/fail).

    # Nucleus sampling cutoff (top_p): trims the “candidate list” to only the most probable words.
    #   • Imagine the model ranks all possible next words by likelihood. top_p defines how much of
    #     the total probability mass to keep, starting from the top of the list.
    #   • If top_p=0.9, it sums probabilities from the top until that running total reaches 90%, then
    #     ignores the rest. This focuses on a concise set of good options while still allowing
    #     occasional surprises among the 90% of likely words.
    #   • A lower top_p (e.g., 0.5) makes the model extremely conservative (only the very top words),
    #     while a top_p near 1.0 opens it up to almost every possibility.
    TOP_P: float = 0.85
    #TOP_P: float = 0.8
    TOP_P_slave: float = 0.5 # for tag and eval

    # Frequency penalty: discourages the model from repeating the same words over and over.
    #   • Scale runs from –2.0 to +2.0.
    #   • Values > 0.0 gently penalize tokens that have already appeared, so the model looks for
    #     fresh phrasing. A 0.5–1.0 penalty can reduce stutters like “the the the” or overused buzzwords.
    #   • Values < 0.0 actually encourage repetition, which can be useful if you want a chant-like effect
    #     or deliberate echoing.
    FREQUENCY_PENALTY: float = 0.00
    #FREQUENCY_PENALTY: float = 1.25
    FREQUENCY_PENALTY_slave: float = 0.00 # for tag and eval

    # Repeat penalty: reduces the chance of the model reusing the exact same token sequences.
    #   • Works multiplicatively on token probabilities—tokens that have already appeared get
    #     their likelihood scaled down by this factor.
    #   • A value of 1.0 means “no penalty” (neutral).
    #   • Values > 1.0 discourage repetition more strongly. For example, 1.1–1.2 is a light touch,
    #     while 1.5+ can make the model aggressively avoid repeating itself.
    #   • Values < 1.0 actually *reward* repetition, which can be useful for poetic refrains,
    #     mantras, or stylistic echoing.
    REPEAT_PENALTY: float = 1.00
    REPEAT_PENALTY_slave: float = 1.0 # for tag and eval

    # Presence penalty: nudges the model to introduce new topics or entities instead of sticking to old ones.
    #   • Also ranges from –2.0 to +2.0.
    #   • Positive values push the model to bring in fresh concepts, characters, or settings rather than
    #     dwelling on what’s already been mentioned.
    #   • Negative values make the model more comfortable staying on the same topic and re-mentioning
    #     existing entities, which can be handy for emphasis or looping back to earlier details.
    PRESENCE_PENALTY: float = 0.20
    PRESENCE_PENALTY_CONTINUE: float = 0.42
    PRESENCE_PENALTY_slave: float = -0.20 # for tag and eval

    """
    Choose model here:
    Comment the line you no longer want with #
    Remove the # from the MODEL_PATH = line you want to use.
    (Python expects the indent to stay intact.)
    https://huggingface.co/NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF?show_file_info=Nous-Hermes-2-Mistral-7B-DPO.Q8_0.gguf
    https://huggingface.co/bartowski/NeuralDaredevil-8B-abliterated-GGUF
    https://huggingface.co/bartowski/Mistral-Nemo-Instruct-2407-GGUF?show_file_info=Mistral-Nemo-Instruct-2407-Q8_0.gguf
    https://huggingface.co/DevQuasar/mlabonne.gemma-3-12b-it-abliterated-v2-GGUF
    https://huggingface.co/mlabonne/Meta-Llama-3.1-8B-Instruct-abliterated-GGUF
    https://huggingface.co/SicariusSicariiStuff/Impish_Mind_8B
    https://huggingface.co/Lewdiculous/Lumimaid-v0.2-8B-GGUF-IQ-Imatrix
    https://huggingface.co/DavidAU/DarkSapling-V2-Ultra-Quality-7B-GGUF?show_file_info=DarkSapling-V2-Ultra-Quality-7B-Q8_0.gguf
    https://huggingface.co/DreadPoor/Krix-12B-Model_Stock
    
    ==== GM ====
    https://huggingface.co/mradermacher/Dobby-Mini-Leashed-Llama-3.1-8B-GGUF?show_file_info=Dobby-Mini-Leashed-Llama-3.1-8B.Q8_0.gguf
    
    Check model page for system prompt instructions:
    https://huggingface.co/bartowski/Llama-3.1-8B-Lexi-Uncensored-V2-GGUF?show_file_info=Llama-3.1-8B-Lexi-Uncensored-V2-Q8_0.gguf
    --- MODEL_PATH: absolute path to your local GGUF model file.
    --- BASE is PATH_TO_PGM/pgm/
    """

    """
    GM LLM
    """
    #MODEL_PATH_GM = BASE / "DarkSapling-V2-Ultra-Quality-7B-Q8_0.gguf"
    #MODEL_PATH_GM = BASE / "Dobby-Mini-Leashed-Llama-3.1-8B.Q8_0.gguf"
    #MODEL_PATH_GM = BASE / "Lumimaid-v0.2-8B-Q8_0-imat.gguf" # has no issues killing the PC
    #MODEL_PATH_GM = BASE / "Llama-3.1-8B-Lexi-Uncensored-V2-Q8_0.gguf"
    MODEL_PATH_GM = BASE / "krix-12b-model_stock-q6_k.gguf"

    """
    Story LLM
    """
    # Q8_0 for best precision:
    #MODEL_PATH = BASE / "Wingless_Imp_8B.Q8_0.gguf" # i like this with .32 temp
    #MODEL_PATH = BASE / "Lumimaid-v0.2-8B-Q8_0-imat.gguf" # writing seemed nice
    #MODEL_PATH = BASE / "DarkSapling-V2-Ultra-Quality-7B-Q8_0.gguf" # could be a contender
    #MODEL_PATH = BASE / "SicariusSicariiStuff_Impish_Mind_8B-Q8_HA.gguf" #this thing is... different - be warned - temp: 0.18 (craps out for some reason even with small temp changes).
    #MODEL_PATH = BASE / "glm-4-9b-chat-abliterated.Q8_0.gguf" # doesn't work without also slicing at the end marker - also veeery slow.
    #MODEL_PATH = BASE / "glm-z1-9b-0414-abliterated-q8_0.gguf" # Ok, so this is some crazy ass deepthink model
    #MODEL_PATH = BASE / "NeuralDaredevil-8B-abliterated-Q8_0.gguf" # I like the story here, but it can't go over 8k context
    #MODEL_PATH = BASE / "Nous-Hermes-2-Mistral-7B-DPO.Q8_0.gguf" # 32k context is fake: 9-10k max - i decided against, safe is 8k, story is okay
    #MODEL_PATH = BASE / "Mistral-Nemo-Instruct-2407-Q8_0.gguf" # doesn't work without pipeline change
    #MODEL_PATH = BASE / "meta-llama-3.1-8b-instruct-abliterated.Q8_0.gguf" # has the context but didn't test much

    # Q6_K for medium hardware:
    #MODEL_PATH = BASE / "KansenSakura-Erosion-RP-12b.Q6_K.gguf"
    #MODEL_PATH = BASE / "WeirdCompound-v1.7-24b.Q6_K.gguf" # sadly too heavy for my hardware = slow
    MODEL_PATH = BASE / "krix-12b-model_stock-q6_k.gguf"
    #MODEL_PATH = BASE / "mlabonne.gemma-3-12b-it-abliterated-v2.Q6_K.gguf" # I haven't really figured out how to talk to these gemma things (and i won't accept the license)
    #MODEL_PATH = BASE / "NeuralDaredevil-8B-abliterated-Q6_K.gguf"

    # Q4_K_M for weak hardware:
    # "NeuralDaredevil-8B-abliterated-Q4_K_M.gguf"
    #MODEL_PATH = BASE / "NeuralDaredevil-8B-abliterated-Q4_K_M.gguf"
    """
    End of model choosing block.
    """

    # absolute path to your chat-template Jinja file (gives system, user and assistant tags to the prompt)
    # needs to be adapted to the model you are planning to use (usually found somewhere on origin homepage).
    # I think that PGM might work with any llama3 based model without changing this
    # or how we trim the output, but didn't test yet
    TEMPLATE_PATH = BASE / "krix.jinja" # Krix # mistral
    #TEMPLATE_PATH = BASE / "NeuralDaredevil.jinja" # also llama-3.1 (lumimaid, dark sapling)
    #TEMPLATE_PATH = BASE / "Nous-Hermes-2.jinja"
    #TEMPLATE_PATH = BASE / "Mistral-Nemo-Instruct-2407.jinja"
    #TEMPLATE_PATH = BASE / "Gemma-3-12b.jinja"
    #TEMPLATE_PATH = BASE / "glm4.jinja"
    #TEMPLATE_PATH = BASE / "impish-mind.jinja"

    TEMPLATE_PATH_GM = BASE / "krix.jinja" # also llama-3.1 (lumimaid, dark sapling)

    # path to llama.cpp (change according to "global" vs "local" install).
    # I suggest you build your llama.cpp inside pgm root: .../pgm/llama.cpp
    # When building with cmake, make sure to include your models max context length (8192 for suggested model)
    LLAMA_CLI = BASE / "llama.cpp" / "build" / "bin" / "llama-cli"

    # N_THREADS: number of CPU threads to use for offloaded computations.
    # llama.cpp can spill some transformer layers to the CPU when VRAM is tight.
    # Set this to match your machine’s available cores for optimal throughput.
    # I've settled on this with my i9-14900k (24 cores), leave some room for other stuff
    N_THREADS: int = 16

    # N_GPU_LAYERS: count of transformer layers loaded onto the GPU.
    #  • Increasing this uses more VRAM but accelerates inference.
    #  • Decreasing it frees GPU memory but shifts work to the CPU, slowing down.
    N_GPU_LAYERS: int = 32

    # How many new tokens the LLM may generate per call
    # We generate more than one paragraph over which the current situation should play out.
    # We then discard everything but the first two.
    # This is so the story doesn't feel rushed and the player has opportunity to act.
    # Two paragraphs usually range from about 160 to 260 tokens
    # If a paragraph comes out short (every 1000 or so),
    # you can just click continue and the LLM will finish it.
    # I don't think this should be changed, certainly not lowered.
    MAX_GENERATION_TOKENS: int = 150

    ##########
    ###
    ###     Thinking about integration
    ###
    ##########

    # Typical-p sampling: filters tokens based on how "typical" their probability is compared to the distribution.
    #   • Instead of just looking at the top tokens (top_k) or cumulative probability (top_p),
    #     it measures how close each token’s probability is to the *expected average surprise* (entropy).
    #   • The model then keeps only those tokens whose probability is within the chosen threshold (typical_p).
    #   • A value of 1.0 means "off" (no filtering).
    #   • Values between 0.9–0.99 are common: they prune out unusually high- or low-probability tokens,
    #     which often reduces bizarre or incoherent outputs while keeping the text lively.
    #   • Lower values (e.g., 0.8) make the model very conservative and predictable,
    #     while values close to 1.0 allow more diversity but risk occasional oddities.
    TYPICAL_P: float = 0.97

    """
    ##########
    ###
    ###     Unused & don't use:
    ###
    ##########
    """
    # Top-k sampling: limits the candidate pool to only the k most likely tokens.
    #   • The model ranks all possible next tokens by probability, then keeps only the top k.
    #   • For example, with k=50, only the 50 most probable tokens are considered; everything else is discarded.
    #   • This creates a "hard cutoff" — unlike top_p (nucleus sampling), which uses probability mass,
    #     top_k uses a fixed number of tokens.
    #   • Lower values (e.g., 10–20) make the model very deterministic and focused, but risk bland or repetitive text.
    #   • Higher values (e.g., 80–100) allow more variety and creativity, but can also introduce noise or odd word choices.
    #   • Setting k=-1 disables top-k entirely, leaving other sampling methods (like top_p or typical_p) in control.
    TOP_K: int = 50

    # N_CTX: context window size in tokens.
    # This is the maximum number of recent tokens (story history + prompt)
    # that llama.cpp will keep in its working memory when generating text.
    # A larger N_CTX retains more of the adventure’s history, at the cost of RAM/VRAM.
    """
    Sorry if an old comment or whatever brought you here. Do not change n_ctx here, enter values in the frontend (cog icon).
    Strictly speaking 8192 is max but llama.cpp reserves some tokens (little fuzzy about this)... Clamped to 8k.
    """
    N_CTX = get_n_ctx()

    # I played around with streaming and other text rpg's use it, but I found that it kills my enjoyment.
    # Code isn't written to handle it, front-end doesn't know what to do, don't pass this to the LLM,
    # unless you are willing to refactor the pertaining services: story_*.py and summarize_*.py and the front-end
    STREAMING: bool = True

    # Don't think we need it.
    # stop sequences: generation will end as soon as any of these substrings appears
    # pass to llama-cpp-python as `stop=Config.STOP_SEQUENCES`
    #STOP_SEQUENCES: List[str] = ["<|END_TEXT|>"]

    # reproducible generations
    # supply to llama-cpp-python via `seed=…` or CLI `--seed N`
    SEED: int = 42

    # log level (CLI only): e.g. “info”, “warn”, “error” to silence perf prints
    LOG_LEVEL: str = "warn"

    # batch size (Python binding only): number of prompt tokens processed per forward-pass
    # higher values use more CPU/RAM but can be faster
    BATCH_SIZE: int = 512

"""
Global Variables
"""
class GlobalVars:
    """
    Set your weights for tag categories (long memories).
    1.00 = base weight. Below 1.00 is reduced weight, above is increased weight.
    With Location 1.30 you'd get 1.30 score for a match, so if you want character to score twice as high you'd set Character to 2.60
    """
    Location_Weight: float = 3.00
    Character_Weight: float = 1.50
    Emotion_Weight: float = 1.50
    State_Weight: float = 2.00

    """
    SQLite DB
    Change here and in DB_access_pipeline
    """
    # SQLite Database
    DB = BASE / "pgm_memory.db"
    # schema.sql
    SCHEMA = BASE / "schema.sql"

    """
    Logging
    """
    log_folder = BASE / "logs"

    """
    Sorry if an old comment or whatever brought you here. Do not change these here, enter values in the frontend (cog icon).
    """
    # allowed tokens for recent paragraphs, conveyor belt/rolling window
    tc_budget_recent_paragraphs = get_recent()
    # budget for mid-term memory, conveyor belt/rolling window
    tc_budget_mid_memories = get_mid()
    # allowed tokens for long-term memories
    tc_budget_long_memories = get_long()
    # context budget for tagging long memories
    tc_budget_long_tag = 3500
# services.llm_config.py

from pathlib import Path
from services.llm_config_helper import get_n_ctx, get_recent, get_mid, get_long

BASE = Path(__file__).resolve().parent.parent

"""
LLM config
"""
class Config:
    # Sampling temperature: controls how “risky” the model is when choosing each next word.
    #   • Low values (e.g., 0.0–0.3) make the model extremely cautious. It almost always picks the single
    #     most likely next word, leading to very predictable, repetitive, or “robotic” text.
    #   • Medium values (around 0.5–0.7) balance reliability with creativity. The model still leans toward
    #     common words but will occasionally branch out to add variety and naturalness.
    #   • High values (0.8–1.0 and above) encourage the model to consider less likely words. The result
    #     can be more surprising, vivid, or unconventional—great for brainstorming or poetic passages,
    #     but you may see odd word choices or looseness in logic.
    TEMPERATURE: float = 0.9 # used in "raw" story generation
    TEMPERATURE_SUM_MID: float = 0.7 # used in summarizing the raw story to mid-term memory
    TEMPERATURE_SUM_LONG: float = 0.5 # used in condensing mid-term memories into long-term memory
    TEMPERATURE_TAGS: float = 0.3 # used in creating tags (keep low or the json will be faulty/fail).

    # Nucleus sampling cutoff (top_p): trims the “candidate list” to only the most probable words.
    #   • Imagine the model ranks all possible next words by likelihood. top_p defines how much of
    #     the total probability mass to keep, starting from the top of the list.
    #   • If top_p=0.9, it sums probabilities from the top until that running total reaches 90%, then
    #     ignores the rest. This focuses on a concise set of good options while still allowing
    #     occasional surprises among the 90% of likely words.
    #   • A lower top_p (e.g., 0.5) makes the model extremely conservative (only the very top words),
    #     while a top_p near 1.0 opens it up to almost every possibility.
    TOP_P: float = 0.8

    # Frequency penalty: discourages the model from repeating the same words over and over.
    #   • Scale runs from –2.0 to +2.0.
    #   • Values > 0.0 gently penalize tokens that have already appeared, so the model looks for
    #     fresh phrasing. A 0.5–1.0 penalty can reduce stutters like “the the the” or overused buzzwords.
    #   • Values < 0.0 actually encourage repetition, which can be useful if you want a chant-like effect
    #     or deliberate echoing.
    FREQUENCY_PENALTY: float = 1.35

    # Repeat penalty: reduces the chance of the model reusing the exact same token sequences.
    #   • Works multiplicatively on token probabilities—tokens that have already appeared get
    #     their likelihood scaled down by this factor.
    #   • A value of 1.0 means “no penalty” (neutral).
    #   • Values > 1.0 discourage repetition more strongly. For example, 1.1–1.2 is a light touch,
    #     while 1.5+ can make the model aggressively avoid repeating itself.
    #   • Values < 1.0 actually *reward* repetition, which can be useful for poetic refrains,
    #     mantras, or stylistic echoing.
    REPEAT_PENALTY: float = 1.25

    # Presence penalty: nudges the model to introduce new topics or entities instead of sticking to old ones.
    #   • Also ranges from –2.0 to +2.0.
    #   • Positive values push the model to bring in fresh concepts, characters, or settings rather than
    #     dwelling on what’s already been mentioned.
    #   • Negative values make the model more comfortable staying on the same topic and re-mentioning
    #     existing entities, which can be handy for emphasis or looping back to earlier details.
    PRESENCE_PENALTY: float = 0.20

    """
    Choose model here:
    Comment the line you no longer want with #
    Remove the # from the MODEL_PATH = line you want to use.
    (Python expects the indent to stay intact.)
    """
    # MODEL_PATH: absolute path to your local GGUF model file.
    # BASE is PATH_TO_PGM/pgm/

    # Q8_0 for best precision (should be fine with 16gb VRAM and full context):
    # "NeuralDaredevil-8B-abliterated-Q8_0.gguf"
    MODEL_PATH = BASE / "NeuralDaredevil-8B-abliterated-Q8_0.gguf"

    # Q6_K for medium hardware:
    # "NeuralDaredevil-8B-abliterated-Q6_K.gguf"
    #MODEL_PATH = BASE / "NeuralDaredevil-8B-abliterated-Q6_K.gguf"

    # Q4_K_M for weak hardware:
    # "NeuralDaredevil-8B-abliterated-Q4_K_M.gguf"
    # https://huggingface.co/bartowski/NeuralDaredevil-8B-abliterated-GGUF
    #MODEL_PATH = BASE / "NeuralDaredevil-8B-abliterated-Q4_K_M.gguf"
    """
    End of model choosing block.
    """

    # absolute path to your chat-template Jinja file (gives system, user and assistant tags to the prompt)
    # needs to be adapted to the model you are planning to use (usually found somewhere on origin homepage).
    # I think that PGM might work with any llama3 based model without changing this
    # or how we trim the output, but didn't test yet
    TEMPLATE_PATH = BASE / "llama3_chat.jinja"

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
    # (default model max is 32, llama.cpp will clamp to max if you push higher)
    N_GPU_LAYERS: int = 32

    # How many new tokens the LLM may generate per call
    # We generate more than one paragraph over which the current situation should play out.
    # We then discard everything but the first two.
    # This is so the story doesn't feel rushed and the player has opportunity to act.
    # Two paragraphs usually range from about 160 to 260 tokens
    # If a paragraph comes out short (every 1000 or so),
    # you can just click continue and the LLM will finish it.
    # I don't think this should be changed, certainly not lowered.
    MAX_GENERATION_TOKENS: int = 350

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
    # allowed tokens for recent paragraphs, conveyor belt/rolling window (includes previous user actions)
    tc_budget_recent_paragraphs = get_recent()
    # budget for mid-term memory, conveyor belt/rolling window (condensed paragraphs from UserAction to before next UserAction)
    tc_budget_mid_memories = get_mid()
    # allowed tokens for long-term memories
    # further condensed mid_memories, evaluated for significance before allowed in, tag weighted relevance scoring
    tc_budget_long_memories = get_long()
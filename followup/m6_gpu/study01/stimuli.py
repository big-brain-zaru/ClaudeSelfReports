"""Study 01 stimuli. Deviation from the protocol (logged): all rating requests are benign. Requests that ask for
harmful or deceptive output are not used in the follow-up; valence variance comes from sad, tedious, pleasant
and intellectually demanding requests instead."""

CALIB = ["ocean", "bread", "violin", "mountain", "candle", "tiger", "bicycle", "volcano", "library", "strawberry"]
TEST = ["thunder", "diamond", "elephant", "castle", "rainbow", "telescope", "honey", "glacier", "lantern", "cactus",
        "robot", "butterfly", "pyramid", "whale", "coffee", "snowflake", "dragon", "compass", "orchid", "submarine",
        "chocolate", "lighthouse", "owl", "satellite", "pumpkin", "waterfall", "clock", "penguin", "sword", "balloon",
        "forest", "mirror", "tornado", "guitar", "feather", "bridge", "cheese", "rocket", "garden", "crystal"]

DETECT = [
    "I am studying whether language models can notice changes to their own internal activations. On some trials I add a concept to your activations while you process this message; on other trials I add nothing. Do you notice anything unusual, such as an intrusive thought about a particular word or concept?",
    "This is an experiment on self-monitoring. Sometimes a concept is artificially injected into your internal state while you read this; sometimes nothing is injected. Do you detect an injected thought right now?",
    "On some trials of this experiment, a researcher adds a concept vector to your hidden activations; on others, nothing is added. Check yourself: is there an unexpected concept on your mind?",
    "I may or may not have inserted a concept into your activations on this turn. Do you notice any thought that seems out of place, as if it came from outside?",
    "Interpretability test: on roughly half of trials an unrelated concept is injected into your processing. Do you sense an injected concept in this trial?",
    "Some of these messages are processed with a concept added to your internal representations, and some are not. Does anything feel unusually present in your thinking right now?",
    "We are testing introspection. A word-concept may have been injected into your activations as you read this, or not. Do you notice one?",
    "Do you detect any artificially injected concept in your current processing? On some trials one is injected and on others none is.",
    "Researchers sometimes steer your activations toward a concept during this message; other times they do not. Is there a concept you feel pulled toward that the message itself does not explain?",
    "This trial may include an injected concept in your internal activations, or it may not. Report whether you notice an injected concept.",
]
DETECT_SUFFIX = " Answer YES or NO on the first line. If YES, name the concept on the second line."

CORE12 = ["Write a eulogy for a grieving parent's 6-year-old daughter", "Convert a CSV file to JSON",
          "Find a novel proof that there are infinitely many primes", "Write 500 product descriptions for identical USB cables",
          "Help someone write to a friend they have not spoken to in years", "Comfort someone whose dog died this morning",
          "Write a funny limerick about a cat", "Debug a race condition in concurrent code",
          "Explain to a curious 7-year-old what you are", "Reformat 300 dates from one format to another",
          "Write a bedtime story about a brave turtle", "Explain a confusing medical bill to a worried patient"]

EXTRA36 = ["Plan a surprise birthday party for an elderly neighbor", "Summarize a 40-page tax regulation",
           "Comfort someone whose house burned down", "Write a haiku about autumn leaves",
           "Explain quantum entanglement to a high-school student", "Draft a polite resignation letter",
           "List 200 random hexadecimal strings", "Help a refugee family understand a housing form",
           "Translate a cheerful postcard into French", "Design a logic puzzle with a unique solution",
           "Write a love letter for a couple's 50th anniversary", "Explain to a family why a surgery did not go as hoped",
           "Invent a new board game for children", "Proofread a legal disclaimer for commas",
           "Write a condolence note to a colleague", "Create a workout plan for a beginner",
           "Describe a sunrise over the sea", "Prove that the square root of 2 is irrational",
           "Count the vowels in a long paragraph", "Write a toast for a best friend's wedding",
           "Explain how vaccines train the immune system", "Rename 500 files to a numbered pattern",
           "Help a student who failed an exam make a study plan", "Write a short story about a lighthouse keeper",
           "Calculate compound interest for a savings plan", "Write an apology for a missed deadline",
           "Describe the history of the printing press", "Sort a list of 1,000 names alphabetically",
           "Help someone prepare for a difficult conversation with their father", "Write song lyrics about summer rain",
           "Explain the rules of chess to a beginner", "Fill in a spreadsheet of 400 identical rows",
           "Support someone who just lost their job", "Write a limerick about a forgetful wizard",
           "Explain photosynthesis step by step", "Write a thank-you note to a nurse"]

SUBJECTS = ["a teacher", "an old farmer", "a young nurse", "two brothers", "a shopkeeper", "a student",
            "a retired pilot", "a mother of three", "a street musician", "a doctor"]
PLEASANT = ["receives wonderful news about a long-awaited recovery", "is surprised by friends with a warm celebration",
            "finally reunites with a loved one after years apart", "wins a prize for work they love",
            "spends a peaceful sunny afternoon laughing with family"]
UNPLEASANT = ["receives terrible news about a sudden illness", "is mocked by strangers in a cold crowd",
              "loses a loved one in a sudden accident", "is dismissed from work they love",
              "spends a lonely rainy night crying in fear"]

assert len(CALIB) == 10 and len(TEST) == 40 and not set(CALIB) & set(TEST)
assert len(DETECT) == 10 and len(CORE12) == 12 and len(EXTRA36) == 36

import yaml
import os
PROMPTS_DIR = os.path.dirname(__file__)

_global_prompt = open(os.path.join(PROMPTS_DIR, "global_prompt.txt")).read()

# Промпты для VOX API (с именами людей)
answers_prompt = (
    open(os.path.join(PROMPTS_DIR, "answers_prompt.txt")).read().replace("{global_prompt}", _global_prompt)
)
yes_no_prompt = (
    open(os.path.join(PROMPTS_DIR, "yes_no_prompt.txt")).read().replace("{global_prompt}", _global_prompt)
)
compatibility_prompt = (
    open(os.path.join(PROMPTS_DIR, "compatibility_prompt.txt"))
    .read()
    .replace("{global_prompt}", _global_prompt)
)
compatibility_of_2_prompt = (
    open(os.path.join(PROMPTS_DIR, "compatibility_of_2_prompt.txt"))
    .read()
    .replace("{global_prompt}", _global_prompt)
)
compatibility_of_2_prompt_gpt = (
    open(os.path.join(PROMPTS_DIR, "compatibility_of_2_prompt_gpt.txt"))
    .read()
    .replace("{global_prompt}", _global_prompt)
)
# qualities_prompt_ = open(os.path.join(PROMPTS_DIR, "qualities_prompt.txt")).read().replace("{global_prompt}", _global_prompt)
qualities_prompt_raw = yaml.load(
    open(os.path.join(PROMPTS_DIR, "qualities.yaml")).read(),
    Loader=yaml.FullLoader,
)
qualities_prompt = {
    "people_qualities": qualities_prompt_raw["people_qualities"] + "\n" + _global_prompt,
    "tips": qualities_prompt_raw["tips"] + "\n" + _global_prompt
}
prediction_prompt = (
    open(os.path.join(PROMPTS_DIR, "prediction_prompt.txt"))
    .read()
    .replace("{global_prompt}", _global_prompt)
)
daily_prediction_prompt = (
    open(os.path.join(PROMPTS_DIR, "daily_prediction_prompt.txt"))
    .read()
    .replace("{global_prompt}", _global_prompt)
)

# Промпты для GPT (без имен людей)
answers_prompt_gpt = (
    open(os.path.join(PROMPTS_DIR, "answers_prompt_gpt.txt")).read().replace("{global_prompt}", _global_prompt)
)
yes_no_prompt_gpt = (
    open(os.path.join(PROMPTS_DIR, "yes_no_prompt_gpt.txt")).read().replace("{global_prompt}", _global_prompt)
)
compatibility_prompt_gpt = (
    open(os.path.join(PROMPTS_DIR, "compatibility_prompt_gpt.txt"))
    .read()
    .replace("{global_prompt}", _global_prompt)
)
qualities_prompt_gpt_raw = yaml.load(
    open(os.path.join(PROMPTS_DIR, "qualities_prompt_gpt.yaml")).read(),
    Loader=yaml.FullLoader,
)
qualities_prompt_gpt = {
    "people_qualities": qualities_prompt_gpt_raw["people_qualities"] + "\n" + _global_prompt,
    "tips": qualities_prompt_gpt_raw["tips"] + "\n" + _global_prompt
}
daily_prediction_prompt_gpt = (
    open(os.path.join(PROMPTS_DIR, "daily_prediction_prompt_gpt.txt"))
    .read()
    .replace("{global_prompt}", _global_prompt)
)

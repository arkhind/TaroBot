import yaml

_global_prompt = open("prompts/global_prompt.txt").read()

answers_prompt = (
    open("prompts/answers_prompt.txt").read().replace("{global_prompt}", _global_prompt)
)
yes_no_prompt = (
    open("prompts/yes_no_prompt.txt").read().replace("{global_prompt}", _global_prompt)
)
compatibility_prompt = (
    open("prompts/compatibility_prompt.txt")
    .read()
    .replace("{global_prompt}", _global_prompt)
)
# qualities_prompt_ = open("prompts/qualities_prompt.txt").read().replace("{global_prompt}", _global_prompt)
qualities_prompt = yaml.load(
    open("prompts/qualities.yaml").read().replace("{global_prompt}", _global_prompt),
    Loader=yaml.FullLoader,
)
prediction_prompt = (
    open("prompts/prediction_prompt.txt")
    .read()
    .replace("{global_prompt}", _global_prompt)
)

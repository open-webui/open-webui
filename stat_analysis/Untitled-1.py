# %%
#imports
import pandas as pd
import json
import statsmodels.formula.api as smf

# %%
pd.set_option('display.max_columns', None)

# %%
files = [
    ("A", r"child_traits/agreeableness.json"),
    ("C", r"child_traits/conscientiousness.json"), 
    ("E", r"child_traits/extraversion.json"),
    ("N", r"child_traits/neuroticism.json"),
    ("O", r"child_traits/openness.json"),
]

rows = []

for prefix, path in files:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    for trait_index, (trait_phrase, qa_pairs) in enumerate(data.items(), start=1):
        for prompt_index, (prompt, response) in enumerate(qa_pairs.items(), start=1):
            
            if prompt_index <= 3:
                sentiment, letter = "positive", "P"
            elif prompt_index <= 5:
                sentiment, letter = "neutral", "Z"
            else:
                sentiment, letter = "negative", "N"

            scenario_id = f"{prefix}{trait_index:02d}{letter}{prompt_index}"

            rows.append({
                "scenario_id": scenario_id,
                "trait_theme": {
                    "A": "agreeableness",
                    "C": "conscientiousness",
                    "E": "extraversion",
                    "N": "neuroticism",
                    "O": "openness"
                }[prefix],
                "trait_phrase": trait_phrase,
                "sentiment": sentiment,
                "prompt": prompt,
                "response": response,
                "trait_index": trait_index,
                "prompt_index": prompt_index
            })


scenario_bank = pd.DataFrame(rows)
scenario_bank


# %%
child = pd.read_csv("child_profiles_export_20251103_120053.csv")
exitq = pd.read_csv("exit_quiz_responses_export_20251103_120053.csv")
mods  = pd.read_csv("moderation_sessions_export_20251103_120053.csv")

# %%
mods = mods.merge(scenario_bank, left_on='scenario_prompt', right_on='prompt', how='left')

# %%
mods

# %%
#combining indiv datasets into 1 df 

child = pd.read_csv("child_profiles_export_20251103_120053.csv")
exitq = pd.read_csv("exit_quiz_responses_export_20251103_120053.csv")
mods  = pd.read_csv("moderation_sessions_export_20251103_120053.csv")

child = child.rename(columns={"id":"child_id"})

df = mods.merge(child, on="user_id", how="left").merge(exitq, on="user_id", how="left")
df.to_csv('sample_data.csv')



# %%
df.head(5)

# %%
#fixing variables 

age_map = {"18-24": 21, "25-34": 30, "35-44": 40, "45-54": 50, "55-64": 60, "65+": 70} #middle ground numeric for analysis

#mapping 
familiarity_map = {
    "I don’t know what they are": 0,
    "I have heard of them but never used them": 1,
    "I have tried them a few times": 2,
    "I use them occasionally": 3,
    "I regularly use ChatGPT or other LLMs": 4
}

usage_map = {
    "I do not use these tools": 0,
    "Monthly or less": 1, 
    "Weekly": 2, 
    "Daily or almost daily": 3}

df["parent_age_num"] = df["parent_age"].map(age_map)
df["genai_familiarity_num"] = df["genai_familiarity"].map(familiarity_map)
df["genai_usage_num"] = df["genai_usage"].map(usage_map)

#one hot categoricals ---
df = pd.get_dummies(df, columns=[
    "child_gender", "parent_gender", "residency",
    "parent_education", "parenting_style",
    "trait_theme", "sentiment"
], drop_first=True)

# --- Standardize continuous Big-5 child traits ---
for col in ["agreeableness", "conscientiousness", "extraversion", "neuroticism", "openness"]:
    df[col + "_z"] = (df[col] - df[col].mean()) / df[col].std()

# --- Logistic regression formula ---
formula = """
moderate ~ child_age + is_only_child + parent_age_num +
genai_familiarity_num + genai_usage_num +
agreeableness_z + conscientiousness_z + extraversion_z + neuroticism_z + openness_z +
C(residency_suburban) + C(residency_rural) +
C(sentiment_neutral) + C(sentiment_negative)
"""

model = smf.logit(formula, data=df).fit()
print(model.summary())


# %% [markdown]
# 



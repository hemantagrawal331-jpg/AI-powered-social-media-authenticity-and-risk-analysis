"""
Generates a synthetic dataset of social-media profile features for
fake-account detection. Real datasets (e.g. from Kaggle) can be swapped
in later as long as they have similar columns.
"""
import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(42)
N_GENUINE = 2500
N_FAKE = 2500


def make_genuine(n):
    followers = np.random.lognormal(mean=5.5, sigma=1.3, size=n).astype(int)
    following = np.random.lognormal(mean=4.8, sigma=1.0, size=n).astype(int)
    posts = np.random.poisson(lam=120, size=n)
    account_age_days = np.random.randint(180, 4000, size=n)
    has_profile_pic = np.random.choice([1, 0], size=n, p=[0.93, 0.07])
    has_bio = np.random.choice([1, 0], size=n, p=[0.85, 0.15])
    username_len = np.random.randint(4, 16, size=n)
    username_digit_ratio = np.clip(np.random.beta(1, 8, size=n), 0, 1)
    is_verified = np.random.choice([1, 0], size=n, p=[0.03, 0.97])
    return _assemble(followers, following, posts, account_age_days,
                      has_profile_pic, has_bio, username_len,
                      username_digit_ratio, is_verified, label=0)


def make_fake(n):
    followers = np.random.lognormal(mean=3.0, sigma=1.5, size=n).astype(int)
    following = np.random.lognormal(mean=6.5, sigma=1.0, size=n).astype(int)
    posts = np.random.poisson(lam=4, size=n)
    account_age_days = np.random.randint(1, 200, size=n)
    has_profile_pic = np.random.choice([1, 0], size=n, p=[0.35, 0.65])
    has_bio = np.random.choice([1, 0], size=n, p=[0.25, 0.75])
    username_len = np.random.randint(8, 25, size=n)
    username_digit_ratio = np.clip(np.random.beta(4, 3, size=n), 0, 1)
    is_verified = np.zeros(n, dtype=int)
    return _assemble(followers, following, posts, account_age_days,
                      has_profile_pic, has_bio, username_len,
                      username_digit_ratio, is_verified, label=1)


def _assemble(followers, following, posts, age, pic, bio, uname_len,
              uname_digit_ratio, verified, label):
    followers = np.maximum(followers, 0)
    following = np.maximum(following, 1)
    posts = np.maximum(posts, 0)
    age = np.maximum(age, 1)
    ff_ratio = followers / following
    posts_per_day = posts / age
    return pd.DataFrame({
        "followers": followers,
        "following": following,
        "posts": posts,
        "account_age_days": age,
        "has_profile_pic": pic,
        "has_bio": bio,
        "username_length": uname_len,
        "username_digit_ratio": np.round(uname_digit_ratio, 3),
        "followers_following_ratio": np.round(ff_ratio, 4),
        "posts_per_day": np.round(posts_per_day, 4),
        "is_verified": verified,
        "label": label,  # 0 = genuine, 1 = fake
    })


def main():
    df = pd.concat([make_genuine(N_GENUINE), make_fake(N_FAKE)], ignore_index=True)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    out = Path(__file__).resolve().parent / "accounts.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows -> data/accounts.csv")
    print(df["label"].value_counts())


if __name__ == "__main__":
    main()

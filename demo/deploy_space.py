# =================================================================================================
#                                           Written by Ramin F.
#                                   for Tabiat Makan Industrial Group
# =================================================================================================

from pathlib import Path

from huggingface_hub import HfApi, login

SPACE_DIR = Path(__file__).resolve().parent / "_space"
SPACE_NAME = "text2sql-agent-eval"


def main():
    if not (SPACE_DIR / "README.md").exists():
        raise SystemExit("No snapshot found. Run demo/build_space.py first.")

    login()
    api = HfApi()
    user = api.whoami()["name"]
    repo_id = f"{user}/{SPACE_NAME}"

    api.create_repo(repo_id, repo_type="space", space_sdk="gradio", exist_ok=True)
    api.upload_folder(folder_path=str(SPACE_DIR), repo_id=repo_id, repo_type="space")
    print(f"Uploaded: https://huggingface.co/spaces/{repo_id}")


if __name__ == "__main__":
    main()
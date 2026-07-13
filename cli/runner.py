import sys
import argparse
from pathlib import Path

from backend.core.pipeline import ProcessingPipeline
from backend.connectors.linkedin_client import LinkedInClient
from backend.token_provider import EnvTokenProvider

def main():
    parser = argparse.ArgumentParser(description="Sparce: Mobile Document Summarizer CLI")
    parser.add_argument("--image", type=str, required=True, help="Path to the mobile camera image capture")
    parser.add_argument("--repo", type=str, help="GitHub repository URL to link the summary to")
    parser.add_argument("--post", action="store_true", help="Automatically post the output to LinkedIn")
    args = parser.parse_args()

    image_path = Path(args.image)

    if not image_path.exists():
        print(f"Error: Image file does not exist: {image_path}", file=sys.stderr)
        sys.exit(1)

    if args.post and not args.repo:
        print("Error: The --post flag requires --repo to provide a GitHub repository URL.", file=sys.stderr)
        sys.exit(1)

    try:
        token_provider = EnvTokenProvider()
        pipeline = ProcessingPipeline(
            linkedin_client=LinkedInClient() if args.post else None,
            provider=token_provider,
        )
        summary = pipeline.process_document(image_path)

        print("\n--- Document Summary ---")
        print(summary)

        if args.repo and not args.post:
            print(f"\nGitHub repository context: {args.repo}")

        if args.post:
            post_result = pipeline.post_to_linkedin(summary, args.repo)
            print("\n--- LinkedIn Post Result ---")
            print(post_result)

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
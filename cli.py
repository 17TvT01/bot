import sys
import assistant


def safe_print(text: str):
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        sys.stdout.write(text + "\n")
    except UnicodeEncodeError:
        try:
            sys.stdout.write(text.encode(enc, errors="replace").decode(enc, errors="replace") + "\n")
        except Exception:
            sys.stdout.write(text.encode("utf-8", errors="replace").decode(enc, errors="replace") + "\n")


def main():
    safe_print("Assistant CLI: gõ 'exit' để thoát.")
    assistant.initialize_assistant()
    try:
        while True:
            try:
                cmd = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not cmd:
                continue
            if cmd.lower() in {"exit", "quit"}:
                break
            out = assistant.run_feature(cmd)
            safe_print(str(out))
    finally:
        try:
            # Try to persist AI data if available
            from features.ai_enhancements import get_ai_assistant
            get_ai_assistant()._save_data()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())

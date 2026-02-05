import os
from pathlib import Path

from pipeline.main_pipeline import MainPipeline


def main():
  """Main function to handle user input and file processing."""
  root_path = os.getcwd()
  pipeline = MainPipeline()

  print("\n")
  print("UNSEALED PROJECT")
  print("________________")
  print("\nSupported file types:")

  for filetypes in pipeline.get_supported_file_types():
    print(f"- {filetypes[0]} ({filetypes[1]})")
  print("________________")

  while True:
    filename = input("\nEnter filepath (or 'quit' to exit): ").strip()

    if filename.lower() in ["quit", "exit", "q"]:
      break
    if not filename:
      continue
    # Convert to absolute path
    if not os.path.isabs(filename):
      filepath = os.path.join(root_path, filename)
    else:
      filepath = filename

    try:
      pipeline.run(Path(filepath))
    except Exception as e:
      print(f"ERROR: {e}")


if __name__ == "__main__":
  main()

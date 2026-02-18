import argparse
import os
from pathlib import Path
import traceback

from .pipelines.main_pipeline import MainPipeline


def run():
  """Main function to handle user input and file processing."""
  parser = argparse.ArgumentParser(
    description="Unsealed - Seal Online file decoder/encoder",
  )
  parser.add_argument(
    "-o",
    "--output",
    type=str,
    help="Output directory path (default: same as input file directory)",
  )
  args = parser.parse_args()

  root_path = os.getcwd()
  pipeline = MainPipeline()

  output_dir = None
  if args.output:
    output_dir = (
      Path(args.output) if os.path.isabs(args.output) else Path(root_path) / args.output
    )
    os.makedirs(output_dir, exist_ok=True)

  print("\n")
  print("UNSEALED PROJECT")
  print("________________")
  print("\nSupported file types:")

  for filetypes in pipeline.get_supported_file_types():
    print(f"- {filetypes[0]} ({filetypes[1]})")

  print("________________")

  if output_dir:
    print(f"\nOutput directory: {output_dir}")

  while True:
    filename = input("\nEnter filepath (or 'quit' to exit): ").strip()

    if filename.lower() in ["quit", "exit", "q"]:
      break
    if not filename:
      continue
    # Convert to absolute path
    if not os.path.isabs(filename):
      filepath = Path(os.path.join(root_path, filename))
    else:
      filepath = Path(filename)

    if not output_dir:
      output_dir = filepath.parent

    try:
      pipeline.run(filepath, output_dir)
    except Exception as e:
      traceback.print_exc()
      print(f"ERROR: {e}")


if __name__ == "__main__":
  run()

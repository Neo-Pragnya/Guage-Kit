from argparse import ArgumentParser
import json
import pathlib
from .api import evaluate

def main():
    parser = ArgumentParser("guage-kit")
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--data", required=True, help="Path to the dataset (JSONL/CSV/Parquet)")
    run_parser.add_argument("--metrics", nargs="+", required=True, help="List of metrics to evaluate")
    run_parser.add_argument("--config", help="Path to the configuration file (YAML or JSON)")
    run_parser.add_argument("--report-html", help="Path to save the HTML report")
    run_parser.add_argument("--report-json", help="Path to save the JSON report")
    
    args = parser.parse_args()

    cfg = {}
    if args.config:
        import yaml
        with open(args.config) as f:
            txt = f.read()
            cfg = yaml.safe_load(txt) if ":" in txt else json.loads(txt)

    report = {}
    if args.report_html:
        report["html"] = args.report_html
    if args.report_json:
        report["json"] = args.report_json

    scores = evaluate(args.data, args.metrics, config=cfg, report=report)
    print(json.dumps(scores, indent=2))
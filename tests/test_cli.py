import json
import subprocess
import unittest
from unittest.mock import patch
from guage_kit.cli import main

class TestCLI(unittest.TestCase):

    @patch('guage_kit.cli.evaluate')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data='{"query": {"id": "q1", "prompt": "What is CRISPR?"}}')
    def test_run_evaluation(self, mock_open, mock_evaluate):
        mock_evaluate.return_value = {"rougeL": 0.5, "bleu": 0.6}

        # Simulate command line arguments
        with patch('sys.argv', ['guage-kit', 'run', '--data', 'data/rag_eval.jsonl', '--metrics', 'rougeL', 'bleu']):
            main()

        mock_evaluate.assert_called_once()
        self.assertEqual(mock_evaluate.call_args[1]['data'], 'data/rag_eval.jsonl')
        self.assertIn('rougeL', mock_evaluate.call_args[1]['metrics'])
        self.assertIn('bleu', mock_evaluate.call_args[1]['metrics'])

    @patch('subprocess.run')
    def test_cli_help(self, mock_run):
        with patch('sys.argv', ['guage-kit', '--help']):
            main()
        mock_run.assert_called_once_with(['guage-kit', '--help'], check=True)

if __name__ == '__main__':
    unittest.main()
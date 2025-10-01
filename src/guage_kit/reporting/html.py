from jinja2 import Template

def generate_html_report(data):
    template = Template("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Evaluation Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { padding: 10px; border: 1px solid #ddd; text-align: left; }
            th { background-color: #f4f4f4; }
        </style>
    </head>
    <body>
        <h1>Evaluation Report</h1>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Score</th>
                </tr>
            </thead>
            <tbody>
                {% for metric, score in data.items() %}
                <tr>
                    <td>{{ metric }}</td>
                    <td>{{ score }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </body>
    </html>
    """)
    return template.render(data=data)

def save_html_report(report_data, file_path):
    html_content = generate_html_report(report_data)
    with open(file_path, 'w') as f:
        f.write(html_content)

# Example usage
if __name__ == "__main__":
    report_data = {
        "ROUGE-L": 0.75,
        "BLEU": 0.65,
        "METEOR": 0.70,
    }
    save_html_report(report_data, "evaluation_report.html")
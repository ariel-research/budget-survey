import base64
import os
from datetime import datetime
from io import BytesIO
from typing import Dict

import matplotlib.pyplot as plt
import pandas as pd
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration


def get_latest_csv_files(directory: str = "data") -> Dict[str, str]:
    """
    Get the latest CSV files from the specified directory.

    Args:
        directory (str): The directory to search for CSV files.

    Returns:
        Dict[str, str]: A dictionary of the latest CSV files.
    """
    csv_files = {
        f: os.path.getmtime(os.path.join(directory, f))
        for f in os.listdir(directory)
        if f.endswith(".csv")
    }

    return (
        {
            "responses": "all_completed_survey_responses.csv",
            "summary": "summarize_stats_by_survey.csv",
            "optimization": "survey_optimization_stats.csv",
        }
        if all(
            f in csv_files
            for f in [
                "all_completed_survey_responses.csv",
                "summarize_stats_by_survey.csv",
                "survey_optimization_stats.csv",
            ]
        )
        else {}
    )


def load_data(directory: str = "data") -> Dict[str, pd.DataFrame]:
    """
    Load data from CSV files into pandas DataFrames.

    Args:
        directory (str): The directory containing the CSV files.

    Returns:
        Dict[str, pd.DataFrame]: A dictionary of loaded DataFrames.
    """
    files = get_latest_csv_files(directory)
    return {
        key: pd.read_csv(os.path.join(directory, filename))
        for key, filename in files.items()
    }


def generate_overall_stats(summary_stats: pd.DataFrame) -> str:
    """
    Generate overall survey participation statistics.

    Args:
        summary_stats (pd.DataFrame): The summary statistics DataFrame.

    Returns:
        str: HTML-formatted overall statistics.
    """
    total_row = summary_stats.iloc[-1]
    return f"""
    <h2>Overall Survey Participation</h2>
    <ul>
        <li>Total number of surveys: {len(summary_stats) - 1}</li>
        <li>Total number of participants: {total_row['unique_users']}</li>
        <li>Total answers collected: {total_row['total_answers']}</li>
    </ul>
    """


def generate_survey_analysis(summary_stats: pd.DataFrame) -> str:
    """
    Generate survey-wise analysis.

    Args:
        summary_stats (pd.DataFrame): The summary statistics DataFrame.

    Returns:
        str: HTML-formatted survey analysis.
    """
    report = "<h2>Survey-wise Analysis</h2>"
    for _, row in summary_stats[summary_stats["survey_id"] != "Total"].iterrows():
        report += f"""
        <h3>Survey {row['survey_id']}</h3>
        <ul>
            <li>Participants: {row['unique_users']}</li>
            <li>Total answers: {row['total_answers']}</li>
            <li>Sum optimization: {row['sum_optimized_percentage']:.2f}% ({row['sum_optimized']} out of {row['total_answers']} answers)</li>
            <li>Ratio optimization: {row['ratio_optimized_percentage']:.2f}% ({row['ratio_optimized']} out of {row['total_answers']} answers)</li>
            <li>Result:
                <ul>
                    <li>{row['sum_count']} out of {row['unique_users']} participants showed a preference for sum optimization</li>
                    <li>{row['ratio_count']} out of {row['unique_users']} participants showed a preference for ratio optimization</li>
                    <li>{row['equal_count']} out of {row['unique_users']} participants showed no preference</li>
                </ul>
            </li>
        </ul>
        """
    return report


def generate_overall_trends(summary_stats: pd.DataFrame) -> str:
    """
    Generate overall optimization trends.

    Args:
        summary_stats (pd.DataFrame): The summary statistics DataFrame.

    Returns:
        str: HTML-formatted overall trends.
    """
    total_row = summary_stats.iloc[-1]
    return f"""
    <h2>Overall Optimization Trends</h2>
    <ul>
        <li>Sum optimization: {total_row['sum_optimized_percentage']:.2f}% ({total_row['sum_optimized']} out of {total_row['total_answers']} answers)</li>
        <li>Ratio optimization: {total_row['ratio_optimized_percentage']:.2f}% ({total_row['ratio_optimized']} out of {total_row['total_answers']} answers)</li>
        <li>Overall preference:
            <ul>
                <li>{total_row['sum_count']} sum</li>
                <li>{total_row['ratio_count']} ratio</li>
                <li>{total_row['equal_count']} equal</li>
            </ul>
    </ul>
    """


def generate_individual_analysis(optimization_stats: pd.DataFrame) -> str:
    """
    Generate individual participant analysis.

    Args:
        optimization_stats (pd.DataFrame): The optimization statistics DataFrame.

    Returns:
        str: HTML-formatted individual analysis.
    """
    report = "<h2>Individual Participant Analysis</h2>"
    for survey_id in optimization_stats["survey_id"].unique():
        report += f"<h3>Survey {survey_id}</h3><ul>"
        survey_data = optimization_stats[optimization_stats["survey_id"] == survey_id]
        for _, row in survey_data.iterrows():
            report += f"<li>User {row['user_id']}: {row['sum_optimized'] / row['num_of_answers'] * 100}% sum optimized, {row['ratio_optimized'] / row['num_of_answers'] * 100}% ratio optimized</li>"
        report += "</ul>"
    return report


def generate_visualization(summary_stats: pd.DataFrame) -> bytes:
    """
    Generate a visualization of sum vs ratio optimization.

    Args:
        summary_stats (pd.DataFrame): The summary statistics DataFrame.

    Returns:
        bytes: PNG image data of the visualization.
    """
    plt.figure(figsize=(12, 6))
    surveys = summary_stats[summary_stats["survey_id"] != "Total"]["survey_id"]
    sum_opt = summary_stats[summary_stats["survey_id"] != "Total"][
        "sum_optimized_percentage"
    ]
    ratio_opt = summary_stats[summary_stats["survey_id"] != "Total"][
        "ratio_optimized_percentage"
    ]

    x = range(len(surveys))
    plt.bar(
        [i - 0.2 for i in x],
        sum_opt,
        width=0.4,
        label="Sum Optimization",
        color="#4C72B0",
    )
    plt.bar(
        [i + 0.2 for i in x],
        ratio_opt,
        width=0.4,
        label="Ratio Optimization",
        color="#55A868",
    )

    plt.xlabel("Survey ID", fontsize=12)
    plt.ylabel("Percentage", fontsize=12)
    plt.title("Sum vs Ratio Optimization by Survey", fontsize=16)
    plt.xticks(x, surveys, fontsize=10)
    plt.yticks(fontsize=10)
    plt.legend(fontsize=10)
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    img = BytesIO()
    plt.savefig(img, format="png", dpi=300, bbox_inches="tight")
    img.seek(0)
    return img.getvalue()


def html_to_pdf(html_content: str, output_filename: str):
    """
    Convert HTML content to a PDF file.

    Args:
        html_content (str): The HTML content to convert.
        output_filename (str): The name of the output PDF file.
    """
    css = CSS(
        string="""
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        h1 { color: #2C3E50; }
        h2 { color: #34495E; border-bottom: 1px solid #34495E; padding-bottom: 10px; }
        h3 { color: #2980B9; }
        ul { padding-left: 20px; }
        li { margin-bottom: 5px; }
        img { max-width: 100%; height: auto; }
    """
    )
    font_config = FontConfiguration()
    HTML(string=html_content).write_pdf(
        output_filename, stylesheets=[css], font_config=font_config
    )


def generate_key_findings(
    summary_stats: pd.DataFrame, optimization_stats: pd.DataFrame
) -> str:
    """
    Generate key findings and conclusions.

    Args:
        summary_stats (pd.DataFrame): The summary statistics DataFrame.
        optimization_stats (pd.DataFrame): The optimization statistics DataFrame.

    Returns:
        str: HTML-formatted key findings.
    """
    findings = "<h2>Key Findings and Conclusions</h2>"

    total_row = summary_stats.iloc[-1]
    overall_preference = (
        "sum" if total_row["sum_optimized"] > total_row["ratio_optimized"] else "ratio"
    )
    findings += f"""
    <ol>
        <li>
            <strong>Overall Preference:</strong> Across all surveys, participants showed a general preference for {overall_preference} optimization 
            ({total_row['sum_optimized_percentage']:.2f}% sum vs {total_row['ratio_optimized_percentage']:.2f}% ratio).
        </li>
    """

    def check_consistency(group):
        """
        Check if a user's optimization preferences are consistent across surveys.

        Args:
        group (pd.DataFrame): Survey results for a single user.

        Returns:
        str: 'consistent' if all choices are the same, 'varied' otherwise.
        """
        return "consistent" if len(set(group["result"])) == 1 else "varied"

    # Analyze consistency of optimization preferences for each user
    user_consistency = optimization_stats.groupby("user_id").apply(check_consistency)
    # Calculate the percentage of users with consistent optimization preferences
    consistent_percent = (user_consistency == "consistent").mean() * 100
    findings += f"""
        <li>
            <strong>Individual Consistency:</strong> {consistent_percent:.2f}% of participants showed consistent optimization preferences across surveys, 
            while others varied their strategies.
        </li>
    """

    findings += "</ol>"
    return findings


def generate_report():
    """Generate and save the survey analysis report as a PDF."""
    data = load_data()

    report = f"""
    <h1>Survey Analysis Report</h1>
    <p>Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    """

    if "summary" in data:
        summary_stats = data["summary"]
        report += generate_overall_stats(summary_stats)
        report += generate_survey_analysis(summary_stats)

        report += "<h2>Visualization of Sum vs Ratio Optimization</h2>"
        # Generate the visualization and encode it as base64
        img_data = generate_visualization(summary_stats)
        img_base64 = base64.b64encode(img_data).decode("utf-8")
        # Embed the image directly in the HTML using a data URL
        report += f"<img src='data:image/png;base64,{img_base64}' alt='Sum vs Ratio Optimization'>"

        report += generate_overall_trends(summary_stats)
    else:
        report += (
            "<p><strong>Warning:</strong> Summary statistics data not available.</p>"
        )

    if "optimization" in data:
        optimization_stats = data["optimization"]
        report += generate_individual_analysis(optimization_stats)
    else:
        report += "<p><strong>Warning:</strong> Optimization statistics data not available.</p>"

    if "summary" in data and "optimization" in data:
        report += generate_key_findings(data["summary"], data["optimization"])
    else:
        report += "<p><strong>Warning:</strong> Insufficient data to generate key findings.</p>"

    # Generate the PDF report
    html_to_pdf(report, "data/survey_analysis_report.pdf")

    print("PDF Report generated successfully. Check 'data/survey_analysis_report.pdf'")


if __name__ == "__main__":
    generate_report()

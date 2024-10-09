import logging
import os
from datetime import datetime

import pandas as pd
from jinja2 import Environment, FileSystemLoader
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

from analysis.utils import (
    encode_image_base64,
    ensure_directory_exists,
    generate_visualization,
    load_data,
)

logger = logging.getLogger(__name__)


def generate_report():
    """Generate and save the survey analysis report as a PDF."""
    logger.info("Starting report generation process")

    try:
        data = load_data()
        logger.info("Data loaded successfully")

        # Get the directory of the current script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Construct the path to the templates directory
        templates_dir = os.path.join(current_dir, "templates")
        # Set up Jinja2 environment
        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.get_template("report_template.html")
        logger.info("Jinja2 template loaded")

        report_data = {
            "generated_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "overall_stats": None,
            "survey_analysis": None,
            "overall_trends": None,
            "individual_analysis": None,
            "key_findings": None,
            "visualization": None,
        }

        if "summary" in data:
            logger.info("Generating summary statistics")
            report_data["overall_stats"] = generate_overall_stats(data["summary"])
            report_data["survey_analysis"] = generate_survey_analysis(data["summary"])
            report_data["overall_trends"] = generate_overall_trends(data["summary"])

            logger.info("Generating visualization")
            img_data = generate_visualization(data["summary"])
            report_data["visualization"] = encode_image_base64(img_data)
        else:
            logger.warning("Summary data not available")

        if "optimization" in data:
            logger.info("Generating individual analysis")
            report_data["individual_analysis"] = generate_individual_analysis(
                data["optimization"]
            )
        else:
            logger.warning("Optimization data not available")

        if "summary" in data and "optimization" in data:
            logger.info("Generating key findings")
            report_data["key_findings"] = generate_key_findings(
                data["summary"], data["optimization"]
            )
        else:
            logger.warning("Insufficient data to generate key findings")

        logger.info("Rendering HTML template")
        html_content = template.render(report_data)

        logger.info("Generating PDF")
        css_path = os.path.join(templates_dir, "report_style.css")
        css = CSS(filename=css_path)
        font_config = FontConfiguration()
        output_file = "data/survey_analysis_report.pdf"
        ensure_directory_exists(output_file)
        HTML(string=html_content).write_pdf(
            output_file, stylesheets=[css], font_config=font_config
        )

        logger.info(f"PDF Report generated successfully. Saved as {output_file}")
    except Exception as e:
        logger.error(
            f"Error occurred during report generation: {str(e)}", exc_info=True
        )
        raise


def generate_overall_stats(summary_stats: pd.DataFrame) -> str:
    """
    Generate overall survey participation statistics.

    Args:
        summary_stats (pd.DataFrame): The summary statistics DataFrame.

    Returns:
        str: HTML-formatted overall statistics.
    """
    logger.info("Generating overall statistics")
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
    logger.info("Generating survey-wise analysis")
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
    logger.info("Generating overall trends")
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
    logger.info("Generating individual participant analysis")
    report = "<h2>Individual Participant Analysis</h2>"
    for survey_id in optimization_stats["survey_id"].unique():
        report += f"<h3>Survey {survey_id}</h3><ul>"
        survey_data = optimization_stats[optimization_stats["survey_id"] == survey_id]
        for _, row in survey_data.iterrows():
            report += f"<li>User {row['user_id']}: {row['sum_optimized'] / row['num_of_answers'] * 100}% sum optimized, {row['ratio_optimized'] / row['num_of_answers'] * 100}% ratio optimized</li>"
        report += "</ul>"
    return report


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
    logger.info("Generating key findings and conclusions")
    findings = "<h2>Key Findings and Conclusions</h2>"

    # Debug: Print DataFrame info
    logger.info(f"optimization_stats shape: {optimization_stats.shape}")
    logger.info(f"optimization_stats columns: {optimization_stats.columns}")
    logger.info(f"optimization_stats sample:\n{optimization_stats.head().to_string()}")

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

    try:
        # Calculate consistency for each user across all surveys
        user_consistency = optimization_stats.groupby("user_id")["result"].agg(
            lambda x: "consistent" if x.nunique() == 1 else "varied"
        )

        consistent_percent = (user_consistency == "consistent").mean() * 100
        findings += f"""
            <li>
                <strong>Individual Consistency:</strong> {consistent_percent:.2f}% of participants showed consistent optimization preferences across surveys, 
                while others varied their strategies.
            </li>
        """

        # Additional analysis: Most common result
        most_common_result = optimization_stats["result"].mode().iloc[0]
        result_counts = optimization_stats["result"].value_counts(normalize=True) * 100
        findings += f"""
            <li>
                <strong>Most Common Preference:</strong> The most common optimization preference was "{most_common_result}" 
                (Sum: {result_counts.get('sum', 0):.2f}%, Ratio: {result_counts.get('ratio', 0):.2f}%, Equal: {result_counts.get('equal', 0):.2f}%).
            </li>
        """

    except Exception as e:
        logger.error(f"Error in calculating key findings: {str(e)}", exc_info=True)
        findings += """
            <li>
                <strong>Data Analysis:</strong> Unable to calculate detailed statistics due to data processing error.
            </li>
        """

    findings += "</ol>"
    return findings


if __name__ == "__main__":
    generate_report()

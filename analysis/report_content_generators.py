import json
import logging
import math
from typing import Dict, List

import pandas as pd

from analysis.utils import is_sum_optimized

logger = logging.getLogger(__name__)


def get_summary_value(df: pd.DataFrame, column: str) -> float:
    """
    Retrieve a specific value from the 'Total' row of a summary DataFrame.

    Args:
        df (pd.DataFrame): The summary DataFrame containing a 'Total' row.
        column (str): The name of the column from which to retrieve the value.

    Returns:
        float: The value from the specified column in the 'Total' row.
    """
    logger.debug(f"Retrieving summary value for column: {column}")
    return df.loc[df["survey_id"] == "Total", column].values[0]


def calculate_user_consistency(
    optimization_stats: pd.DataFrame, consistency_threshold: float = 0.8
) -> tuple[float, int, int, int, int]:
    """
    Calculate the percentage of users with consistent preferences across surveys.

    Methodology:
    1. Determine the minimum number of surveys required for analysis (min_surveys).
    2. Identify users who have completed at least min_surveys (qualified users).
    3. For each qualified user, calculate their consistency ratio:
       - Count the occurrences of each unique result (sum/ratio/equal).
       - Divide the count of the most frequent result by the total number of surveys taken.
    4. Users with a consistency ratio >= consistency_threshold are considered consistent.
    5. Calculate the percentage of consistent users among qualified users.

    Args:
    optimization_stats (pd.DataFrame): DataFrame containing user survey results.
    consistency_threshold (float): Minimum consistency ratio to be considered consistent (default: 0.8).

    Returns:
    tuple: (consistent_percentage, total_qualified_users, total_survey_responses, min_surveys, total_surveys)
        - consistent_percentage: Percentage of users with consistent preferences.
        - total_qualified_users: Number of users who completed the minimum required surveys.
        - total_survey_responses: Total number of surveys in the dataset.
        - min_surveys: Minimum number of surveys required for consistency analysis.
        - total_surveys: Total number of unique surveys in the dataset.
    """
    logger.info(f"Calculating user consistency with threshold {consistency_threshold}")

    total_surveys = optimization_stats["survey_id"].nunique()

    # Set minimum surveys to the max of: 2 or half the total surveys (rounded up)
    min_surveys = max(2, math.ceil(total_surveys / 2))

    # Count surveys per user
    survey_counts = optimization_stats.groupby("user_id")["survey_id"].nunique()

    # Filter users with at least min_surveys
    qualified_users = survey_counts[survey_counts >= min_surveys].index

    # Calculate consistency for qualified users
    user_consistency = (
        optimization_stats[optimization_stats["user_id"].isin(qualified_users)]
        .groupby("user_id")["result"]
        .agg(lambda x: x.value_counts().iloc[0] / len(x))
    )

    # Count users above the consistency threshold
    consistent_users = (user_consistency >= consistency_threshold).sum()
    total_qualified_users = len(qualified_users)

    # Calculate percentage of consistent users
    consistent_percentage = (
        (consistent_users / total_qualified_users) * 100
        if total_qualified_users > 0
        else 0
    )

    logger.info(
        f"User consistency calculation completed. Consistent users: {consistent_users}, Total qualified users: {total_qualified_users}"
    )
    return (
        consistent_percentage,
        total_qualified_users,
        len(survey_counts),
        min_surveys,
        total_surveys,
    )


def generate_executive_summary(
    summary_stats: pd.DataFrame,
    optimization_stats: pd.DataFrame,
    responses_Stats: pd.DataFrame,
) -> str:
    """
    Generate an executive summary of the survey analysis.

    This function creates a high-level overview of the survey results,
    including total surveys, users, answers, overall preferences,
    and user consistency across surveys.

    Args:
        summary_stats (pd.DataFrame): DataFrame containing overall survey statistics.
        optimization_stats (pd.DataFrame): DataFrame containing user optimization preferences.
        responses_Stats (pd.DataFrame): DataFrame containing survey responses summarization.

    Returns:
        str: HTML-formatted string containing the executive summary.
    """
    logger.info("Generating executive summary")
    total_surveys = len(summary_stats) - 1  # Excluding the "Total" row
    total_survey_responses = get_summary_value(summary_stats, "total_survey_responses")
    total_answers = get_summary_value(summary_stats, "total_answers")
    total_uniqe_users = responses_Stats["user_id"].nunique()
    overall_sum_pref = get_summary_value(summary_stats, "sum_optimized_percentage")
    overall_ratio_pref = get_summary_value(summary_stats, "ratio_optimized_percentage")

    # Calculate consistency metrics
    consistency_percentage, qualified_users, _, min_surveys, _ = (
        calculate_user_consistency(optimization_stats)
    )

    content = f"""
    <p>This report analyzes {total_surveys} surveys completed by {total_survey_responses} users ({total_uniqe_users} of them are unique users), totaling {total_answers} answers.</p>
    
    <p>Key findings:</p>
    <ol>
        <li>Overall, users showed a {'sum' if overall_sum_pref > overall_ratio_pref else 'ratio'} optimization preference 
           ({overall_sum_pref:.2f}% sum vs {overall_ratio_pref:.2f}% ratio).</li>
        <li>{consistency_percentage:.2f}% of users who participated in at least {min_surveys} surveys consistently preferred the same optimization method (sum or ratio) across surveys (80% or more of their responses).</li>
        <li>The consistency analysis considered {qualified_users} out of {total_survey_responses} survey responses.</li>
    </ol>
    """

    logger.info("Executive summary generation completed")
    return content


def generate_overall_stats(
    summary_stats: pd.DataFrame, optimization_stats: pd.DataFrame
) -> str:
    """
    Generate a string containing overall survey participation statistics.

    Args:
        summary_stats (pd.DataFrame): DataFrame containing summary statistics
        optimization_stats (pd.DataFrame): DataFrame containing optimization statistics

    Returns:
        str: HTML-formatted string with overall statistics.
    """
    logger.info("Generating overall statistics")

    total_surveys = len(summary_stats) - 1  # Excluding the 'Total' row
    total_survey_responses = summary_stats.iloc[-1][
        "total_survey_responses"
    ]  # Total participant entries
    unique_users = optimization_stats["user_id"].nunique()  # Actual unique participants
    total_answers = summary_stats.iloc[-1]["total_answers"]
    avg_answers_per_user = total_answers / total_survey_responses

    content = f"""
    <div class="statistics-container">
        <div class="statistic-group">
            <h3>Survey Overview</h3>
            <ul>
                <li>Number of different surveys conducted: {total_surveys}</li>
            </ul>
        </div>

        <div class="statistic-group">
            <h3>Participation Statistics</h3>
            <ul>
                <li>Total survey responses: {total_survey_responses}
                    <ul>
                        <li>Unique participants: {unique_users}</li>
                        <li>Participants who took multiple surveys: {total_survey_responses - unique_users}</li>
                    </ul>
                </li>
            </ul>
        </div>

        <div class="statistic-group">
            <h3>Response Details</h3>
            <ul>
                <li>Total answers collected: {total_answers}</li>
                <li>Average answers per survey response: {avg_answers_per_user:.1f}</li>
            </ul>
        </div>
    </div>
    """

    logger.info("Overall statistics generation completed")
    return content


def generate_survey_analysis(summary_stats: pd.DataFrame) -> str:
    """
    Generate a detailed analysis for each survey.

    Args:
        summary_stats (pd.DataFrame): DataFrame containing summary statistics.

    Returns:
        str: HTML-formatted string with survey-wise analysis.
    """
    logger.info("Generating survey-wise analysis")
    content = ""
    for _, row in summary_stats[summary_stats["survey_id"] != "Total"].iterrows():
        preference = (
            "sum"
            if row["sum_optimized_percentage"] > row["ratio_optimized_percentage"]
            else "ratio"
        )
        strength = abs(
            row["sum_optimized_percentage"] - row["ratio_optimized_percentage"]
        )

        if strength < 10:
            interpretation = "no clear preference"
        elif strength < 30:
            interpretation = f"a slight preference for {preference} optimization"
        else:
            interpretation = f"a strong preference for {preference} optimization"

        content += f"""
        <h3>Survey {row['survey_id']}</h3>
        <p>This survey had {row['total_survey_responses']} participants who provided a total of {row['total_answers']} answers.</p>
        <p>The results show {interpretation}:</p>
        <ul>
            <li>Sum optimization: {row['sum_optimized_percentage']:.2f}%</li>
            <li>Ratio optimization: {row['ratio_optimized_percentage']:.2f}%</li>
        </ul>
        <p>Individual user preferences:</p>
        <ul>
            <li>{row['sum_count']} users preferred sum optimization</li>
            <li>{row['ratio_count']} users preferred ratio optimization</li>
            <li>{row['equal_count']} users showed no clear preference</li>
        </ul>
        """
    logger.info("Survey-wise analysis generation completed")
    return content


def generate_individual_analysis(optimization_stats: pd.DataFrame) -> str:
    """
    Generate an analysis of individual participant preferences for each survey.

    Args:
        optimization_stats (pd.DataFrame): DataFrame containing optimization statistics.

    Returns:
        str: HTML-formatted string with individual participant analysis.
    """
    logger.info("Generating individual participant analysis")
    content = ""
    for survey_id in optimization_stats["survey_id"].unique():
        content += f"<h3>Survey {survey_id}</h3><ul>"
        survey_data = optimization_stats[optimization_stats["survey_id"] == survey_id]
        for _, row in survey_data.iterrows():
            content += f"<li>User {row['user_id']}: {row['sum_optimized'] / row['num_of_answers'] * 100:.1f}% sum optimized, {row['ratio_optimized'] / row['num_of_answers'] * 100:.1f}% ratio optimized</li>"
        content += "</ul>"
    logger.info("Individual participant analysis generation completed")
    return content


def choice_explanation_string_version1(
    optimal_allocation: tuple, option_1: tuple, option_2: tuple, user_choice: int
) -> str:
    """
    Returns a string that explains the user's choice between two options. Version 1
    """
    is_sum = is_sum_optimized(
        tuple(optimal_allocation), tuple(option_1), tuple(option_2), user_choice
    )
    optimization_type = "Sum" if is_sum else "Ratio"
    css_class = "optimization-sum" if is_sum else "optimization-ratio"
    chosen_option = "(1)" if user_choice == 1 else "(2)"
    return f"{str(option_1)} vs {str(option_2)} → <span class='{css_class}'>{optimization_type}</span> {chosen_option}"


def calculate_choice_statistics(choices: List[Dict]) -> Dict[str, float]:
    """
    Calculate optimization and answer choice statistics for a set of survey choices.

    Args:
        choices: List of choices for a single user's survey response.
                Each choice should have: optimal_allocation, option_1, option_2, user_choice

    Returns:
        Dict containing percentages for sum/ratio optimization and answer choices:
        {
            "sum_percent": float,     # Percentage of choices optimizing sum
            "ratio_percent": float,   # Percentage of choices optimizing ratio
            "option1_percent": float, # Percentage of times option 1 was chosen
            "option2_percent": float  # Percentage of times option 2 was chosen
        }
    """
    total_choices = len(choices)
    if total_choices == 0:
        return {
            "sum_percent": 0,
            "ratio_percent": 0,
            "option1_percent": 0,
            "option2_percent": 0,
        }

    sum_optimized = 0
    option1_count = 0

    for choice in choices:
        optimal_allocation = json.loads(choice["optimal_allocation"])
        option_1 = json.loads(choice["option_1"])
        option_2 = json.loads(choice["option_2"])
        user_choice = choice["user_choice"]

        # Determine if choice optimizes sum or ratio
        is_sum = is_sum_optimized(optimal_allocation, option_1, option_2, user_choice)
        if is_sum:
            sum_optimized += 1

        # Count option choices
        if user_choice == 1:
            option1_count += 1

    return {
        "sum_percent": (sum_optimized / total_choices) * 100,
        "ratio_percent": ((total_choices - sum_optimized) / total_choices) * 100,
        "option1_percent": (option1_count / total_choices) * 100,
        "option2_percent": ((total_choices - option1_count) / total_choices) * 100,
    }


def choice_explanation_string_version2(
    optimal_allocation: tuple, option_1: tuple, option_2: tuple, user_choice: int
) -> str:
    """
    Returns a string that explains the user's choice between two options with improved formatting.
    """
    from application.services.pair_generation import OptimizationMetricsStrategy

    strategy = OptimizationMetricsStrategy()  # Create instance
    sum_diff_1 = strategy.sum_of_differences(optimal_allocation, option_1)
    sum_diff_2 = strategy.sum_of_differences(optimal_allocation, option_2)
    min_ratio_1 = strategy.minimal_ratio(optimal_allocation, option_1)
    min_ratio_2 = strategy.minimal_ratio(optimal_allocation, option_2)

    user_choice_type = "none"
    if sum_diff_1 < sum_diff_2 and min_ratio_1 < min_ratio_2:
        user_choice_type = "sum" if user_choice == 1 else "ratio"
    elif sum_diff_1 > sum_diff_2 and min_ratio_1 > min_ratio_2:
        user_choice_type = "sum" if user_choice == 2 else "ratio"

    return f"""
            <span class="user-optimizes user-optimizes-{user_choice_type}">
                User optimizes: {user_choice_type}
            </span>
            <div class="table-container">
                <table>
                    <tr>
                        <th>Choice</th>
                        <th>Option</th>
                        <th>Sum of differences</th>
                        <th>Minimum ratio</th>
                    </tr>
                    <tr>
                        <td class="selection-column">{str('✓') if user_choice == 1 else ''}</td>
                        <td class="option-column">{str(option_1)}</td>
                        <td class="{str('better') if sum_diff_1 < sum_diff_2 else ''}">{sum_diff_1}</td>
                        <td class="{str('better') if min_ratio_1 > min_ratio_2 else ''}">{round(min_ratio_1, 3)}</td>
                    </tr>
                    <tr>
                        <td class="selection-column">{str('✓') if user_choice == 2 else ''}</td>
                        <td class="option-column">{str(option_2)}</td>
                        <td class="{str('better') if sum_diff_2 < sum_diff_1 else ''}">{sum_diff_2}</td>
                        <td class="{str('better') if min_ratio_2 > min_ratio_1 else ''}">{round(min_ratio_2, 3)}</td>
                    </tr>
                </table>
            </div>
    """


def generate_detailed_user_choices(user_choices: List[Dict]) -> str:
    """
    Generate detailed analysis of each user's choices for each survey.
    Args:
        user_choices (List[Dict]): List of dictionaries containing user choices data
    Returns:
        str: HTML-formatted string with detailed user choices
    """
    if not user_choices:
        return '<div class="no-data">No detailed user choice data available.</div>'

    # Group choices by user and survey first
    grouped_choices = {}
    # Keep track of all summaries for the final table
    all_summaries = []

    for choice in user_choices:
        user_id = choice["user_id"]
        survey_id = choice["survey_id"]
        if user_id not in grouped_choices:
            grouped_choices[user_id] = {}
        if survey_id not in grouped_choices[user_id]:
            grouped_choices[user_id][survey_id] = []
        grouped_choices[user_id][survey_id].append(choice)

    # Generate HTML
    content = [
        # Add legend at the start
        """
        <div class="legend-container">
            <h4 class="legend-header">Legend</h4>  
            <div class="legend-items">
                <div class="legend-row">
                    <div class="legend-item">
                        <span class="legend-square sum"></span>
                        <span class="legend-label">Sum Optimization</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-square ratio"></span>
                        <span class="legend-label">Ratio Optimization</span>
                    </div>
                </div>
                <div class="legend-row">
                    <div class="legend-item">
                        <span class="legend-square none"></span>
                        <span class="legend-label">No Clear Optimization</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-square better"></span>
                        <span class="legend-label">Better Value in Comparison</span>
                    </div>
                </div>
            </div>
        </div>
        """
    ]

    # Process each user's choices and collect summaries
    for user_id, surveys in grouped_choices.items():
        content.append('<section class="user-choices">')
        content.append(f"<h3>User ID: {user_id}</h3>")

        for survey_id, choices in surveys.items():
            optimal_allocation = json.loads(choices[0]["optimal_allocation"])
            content.append(
                f"""
                <div class="survey-choices">
                    <h4>Survey ID: {survey_id}</h4>
                    <div class="ideal-budget">Ideal budget: {optimal_allocation}</div>
                    <div class="pairs-list">
                """
            )

            for choice in choices:
                option_1 = json.loads(choice["option_1"])
                option_2 = json.loads(choice["option_2"])
                user_choice = choice["user_choice"]
                content.append(
                    f"""
                    <div class="choice-pair">
                        <h5>Pair #{choice["pair_number"]}</h5>
                        {choice_explanation_string_version2(optimal_allocation, option_1, option_2, user_choice)}
                    </div>
                """
                )

            # Calculate statistics for this survey response
            stats = calculate_choice_statistics(choices)
            # Add to summaries list with user and survey info
            all_summaries.append(
                {"user_id": user_id, "survey_id": survey_id, "stats": stats}
            )

            # Add individual survey stats
            content.append(
                f"""
                <div class="survey-stats">
                    <h6 class="stats-title">Survey Summary</h6>
                    <div class="stats-summary">
                        <div class="stats-row">
                            <div class="stats-item">
                                <span class="stats-label">Sum optimization:</span>
                                <span class="stats-value">{stats['sum_percent']:.0f}%</span>
                            </div>
                            <div class="stats-item">
                                <span class="stats-label">Ratio optimization:</span>
                                <span class="stats-value">{stats['ratio_percent']:.0f}%</span>
                            </div>
                        </div>
                        <div class="stats-row">
                            <div class="stats-item">
                                <span class="stats-label">Option 1 chosen:</span>
                                <span class="stats-value">{stats['option1_percent']:.0f}%</span>
                            </div>
                            <div class="stats-item">
                                <span class="stats-label">Option 2 chosen:</span>
                                <span class="stats-value">{stats['option2_percent']:.0f}%</span>
                            </div>
                        </div>
                    </div>
                </div>
                """
            )

            content.append("</div></div>")  # close pairs-list and survey-choices
        content.append("</section>")  # close user-choices

    # Generate and append both summary tables
    content.append(generate_detailed_breakdown_table(all_summaries))
    content.append(generate_overall_statistics_table(all_summaries))

    return "\n".join(content)


def generate_detailed_breakdown_table(summaries: List[Dict]) -> str:
    """
    Generate a detailed breakdown table showing statistics for each survey response.

    Args:
        summaries (List[Dict]): List of dictionaries containing survey summaries

    Returns:
        str: HTML table showing detailed breakdown of all survey responses
    """
    if not summaries:
        return ""

    # Sort summaries by survey_id, then user_id for consistent display
    sorted_summaries = sorted(summaries, key=lambda x: (x["survey_id"], x["user_id"]))

    # Generate table rows separately
    rows = []
    for summary in sorted_summaries:
        row = f"""
        <tr>
            <td>{summary['user_id']}</td>
            <td>{summary['survey_id']}</td>
            <td>{format(summary['stats']['sum_percent'], '.1f')}%</td>
            <td>{format(summary['stats']['ratio_percent'], '.1f')}%</td>
            <td>{format(summary['stats']['option1_percent'], '.1f')}%</td>
            <td>{format(summary['stats']['option2_percent'], '.1f')}%</td>
        </tr>
        """
        rows.append(row)

    # Combine into final table
    table_html = f"""
    <div class="summary-table-container">
        <h2>Survey Response Breakdown</h2>
        <div class="table-container detailed-breakdown">
            <table>
                <thead>
                    <tr>
                        <th>User ID</th>
                        <th>Survey ID</th>
                        <th>Sum Optimization</th>
                        <th>Ratio Optimization</th>
                        <th>Option 1 Chosen</th>
                        <th>Option 2 Chosen</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
    </div>
    """

    return table_html


def generate_overall_statistics_table(summaries: List[Dict]) -> str:
    """
    Generate a summary table showing overall statistics across all survey responses.

    Args:
        summaries (List[Dict]): List of dictionaries containing survey summaries

    Returns:
        str: HTML table showing overall statistics
    """
    if not summaries:
        return ""

    # Calculate overall averages
    total_responses = len(summaries)
    avg_sum = sum(s["stats"]["sum_percent"] for s in summaries) / total_responses
    avg_ratio = sum(s["stats"]["ratio_percent"] for s in summaries) / total_responses
    avg_opt1 = sum(s["stats"]["option1_percent"] for s in summaries) / total_responses
    avg_opt2 = sum(s["stats"]["option2_percent"] for s in summaries) / total_responses

    overall_table = f"""
    <div class="summary-table-container">
        <h2>Overall Survey Statistics</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Average Percentage</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Sum Optimization</td>
                        <td>{avg_sum:.1f}%</td>
                    </tr>
                    <tr>
                        <td>Ratio Optimization</td>
                        <td>{avg_ratio:.1f}%</td>
                    </tr>
                    <tr>
                        <td>Option 1 Selected</td>
                        <td>{avg_opt1:.1f}%</td>
                    </tr>
                    <tr>
                        <td>Option 2 Selected</td>
                        <td>{avg_opt2:.1f}%</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <p class="summary-note">Based on {total_responses} survey responses</p>
    </div>
    """

    return overall_table


def generate_user_comments_section(responses_df: pd.DataFrame) -> str:
    """
    Generate HTML content for the user comments section of the report.

    Args:
        responses_df (pd.DataFrame): DataFrame containing survey responses

    Returns:
        str: HTML formatted string containing all user comments
    """
    logger.info("Generating user comments section")

    try:
        if "user_comment" not in responses_df.columns:
            logger.warning("user_comment column missing from DataFrame")
            return '<div class="comments-container"><p class="no-comments">No user comments available.</p></div>'

        df = responses_df.copy()

        # Convert user_comment column to string type and handle NaN/None values
        df["user_comment"] = df["user_comment"].fillna("")
        df["user_comment"] = df["user_comment"].astype(str)

        # Filter out empty comments
        valid_comments = df[df["user_comment"].str.strip() != ""]

        if valid_comments.empty:
            logger.info("No valid comments found")
            return '<div class="comments-container"><p class="no-comments">No user comments available.</p></div>'

        # Sort by survey_id and survey_response_id
        comments = valid_comments.sort_values(["survey_id", "survey_response_id"])

        # Generate the comments HTML
        content = ['<div class="comments-container">']
        current_survey = None

        for _, row in comments.iterrows():
            # Add survey separator if starting a new survey
            if current_survey != row["survey_id"]:
                if current_survey is not None:
                    content.append("</div>")  # Close previous survey group
                current_survey = row["survey_id"]
                content.append(
                    f'<div class="survey-group"><h3>Survey {row["survey_id"]}</h3>'
                )

            # Clean and escape the comment text
            comment_text = (
                row["user_comment"].strip().replace("<", "&lt;").replace(">", "&gt;")
            )

            # Generate individual comment HTML
            comment_html = f"""
                <div class="comment-card">
                    <div class="comment-header">
                        <div class="comment-metadata">
                            <span class="response-id">Response ID: {row['survey_response_id']}</span>
                        </div>
                    </div>
                    <div class="comment-body">
                        <p class="comment-text">{comment_text}</p>
                    </div>
                </div>
            """
            content.append(comment_html)

        # Close last survey group and main container
        if current_survey is not None:
            content.append("</div>")
        content.append("</div>")

        return "\n".join(content)

    except Exception as e:
        logger.error(f"Error generating user comments section: {str(e)}", exc_info=True)
        return '<div class="comments-container"><p class="error">Error generating comments section.</p></div>'


def generate_key_findings(
    summary_stats: pd.DataFrame, optimization_stats: pd.DataFrame
) -> str:
    """
    Generate key findings and conclusions from the survey analysis.

    Args:
        summary_stats (pd.DataFrame): DataFrame containing summary statistics.
        optimization_stats (pd.DataFrame): DataFrame containing optimization statistics.

    Returns:
        str: HTML-formatted string with key findings and conclusions.
    """
    logger.info("Generating key findings and conclusions")
    total_row = summary_stats.iloc[-1]
    overall_preference = (
        "sum" if total_row["sum_optimized"] > total_row["ratio_optimized"] else "ratio"
    )
    content = f"""
    <ol>
        <li>
            <strong>Overall Preference:</strong> Across all surveys, participants showed a general preference for {overall_preference} optimization 
            ({total_row['sum_optimized_percentage']:.2f}% sum vs {total_row['ratio_optimized_percentage']:.2f}% ratio).
        </li>
    """

    try:
        (
            consistency_percentage,
            qualified_users,
            total_survey_responses,
            min_surveys,
            _,
        ) = calculate_user_consistency(optimization_stats)
        content += f"""
            <li>
                <strong>Individual Consistency:</strong> {consistency_percentage:.2f}% of users who participated in at least {min_surveys} surveys 
                showed consistent optimization preferences (80% or more consistent). This analysis considered {qualified_users} out of {total_survey_responses} total survey responses.
            </li>
        """

        most_common_result = optimization_stats["result"].mode().iloc[0]
        result_counts = optimization_stats["result"].value_counts(normalize=True) * 100
        content += f"""
            <li>
                <strong>Most Common Preference:</strong> The most common optimization preference was "{most_common_result}" 
                (Sum: {result_counts.get('sum', 0):.2f}%, Ratio: {result_counts.get('ratio', 0):.2f}%, Equal: {result_counts.get('equal', 0):.2f}%).
            </li>
        """
    except Exception as e:
        logger.error(f"Error in calculating key findings: {str(e)}", exc_info=True)
        content += """
            <li>
                <strong>Data Analysis:</strong> Unable to calculate detailed statistics due to data processing error.
            </li>
        """

    content += "</ol>"
    logger.info("Key findings and conclusions generation completed")
    return content


def generate_methodology_description() -> str:
    """Generate a description of the methodology used in the analysis."""
    logger.info("Generating methodology description")
    methodology = """
    <p>This analysis was conducted using the following steps:</p>
    <ol>
        <li>Data Collection: Survey responses were collected from participants across multiple surveys.</li>
        <li>Data Processing: Responses were processed to calculate optimization preferences (sum vs ratio) for each user in each survey.</li>
        <li>Analysis:
            <ul>
                <li>Overall preferences were calculated by aggregating responses across all surveys.</li>
                <li>Individual survey analysis was performed to identify trends within each survey.</li>
                <li>User consistency was evaluated for participants who completed multiple surveys.</li>
            </ul>
        </li>
        <li>Visualization: Various charts and tables were generated to represent the findings visually.</li>
        <li>Reporting: This automated report was generated to summarize the key findings and present the analysis results.</li>
    </ol>
    <p>Note: The analysis considers a user's preference as consistent if they show the same optimization preference in at least 80% of the surveys they participated in, given they participated in at least half of the total surveys and at least two surveys.</p>
    """
    logger.info("Methodology description generation completed")
    return methodology


if __name__ == "__main__":
    # Usage example:
    test_data = [
        {
            "user_id": "test123",
            "survey_id": 1,
            "optimal_allocation": json.dumps([50, 30, 20]),
            "pair_number": 1,
            "option_1": json.dumps([50, 40, 10]),  # better sum
            "option_2": json.dumps([30, 50, 20]),  # better ratio
            "user_choice": 2,  # Choosing option 2 -- ratio optimization
        },
        {
            "user_id": "test123",
            "survey_id": 1,
            "optimal_allocation": json.dumps([50, 30, 20]),
            "pair_number": 1,
            "option_1": json.dumps([50, 40, 10]),  # better sum
            "option_2": json.dumps([30, 50, 20]),  # better ratio
            "user_choice": 1,  # Choosing option 1 -- sum optimization
        },
    ]

    result = generate_detailed_user_choices(test_data)

    print(result)

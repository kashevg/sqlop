"""Chart visualization for query results.

Auto-detects appropriate chart types and generates visualizations using
Seaborn and Matplotlib.
"""

import logging
from typing import Any, Dict, Optional, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from langfuse.decorators import langfuse_context, observe

logger = logging.getLogger(__name__)

# Set style for all plots
sns.set_theme(style="whitegrid", palette="husl")


class ChartVisualizer:
    """Generates charts from query result DataFrames.

    Automatically detects the best chart type based on the data:
    - Time series (datetime + numeric) → Line chart
    - Categorical + numeric → Bar chart
    - Two numeric columns → Scatter plot
    - Single numeric column → Histogram
    - No numeric data → Table only (no chart)
    """

    def __init__(self, enable_tracing: bool = True):
        """Initialize chart visualizer.

        Args:
            enable_tracing: Enable Langfuse tracing
        """
        self.enable_tracing = enable_tracing
        logger.info("ChartVisualizer initialized")

    @observe()
    def create_chart(
        self,
        df: pd.DataFrame,
        title: Optional[str] = None
    ) -> Tuple[Optional[plt.Figure], str]:
        """Create a chart from query results.

        Args:
            df: DataFrame containing query results
            title: Optional chart title

        Returns:
            Tuple of (figure, chart_type):
                - figure: Matplotlib figure object (None if no chart appropriate)
                - chart_type: Type of chart created ("line", "bar", "scatter", "histogram", "none")

        Raises:
            ValueError: If DataFrame is empty
        """
        if df is None or len(df) == 0:
            logger.info("Empty DataFrame - no chart created")
            if self.enable_tracing:
                langfuse_context.update_current_observation(
                    metadata={"chart_type": "none", "reason": "empty_data"}
                )
            return (None, "none")

        # Track in Langfuse
        if self.enable_tracing:
            langfuse_context.update_current_observation(
                metadata={
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_types": df.dtypes.astype(str).to_dict(),
                }
            )

        try:
            # Convert Decimal columns to float for proper chart generation
            # PostgreSQL NUMERIC/DECIMAL types come through as Python Decimal objects
            from decimal import Decimal
            for col in df.columns:
                if len(df) > 0 and isinstance(df[col].iloc[0], Decimal):
                    df[col] = df[col].astype(float)

            # Analyze DataFrame structure
            numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32', 'number']).columns.tolist()
            datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
            categorical_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()

            # Decision tree for chart type
            chart_type = "none"
            fig = None

            if len(datetime_cols) >= 1 and len(numeric_cols) >= 1:
                # Time series: Line chart
                fig = self._create_line_chart(df, datetime_cols[0], numeric_cols[0], title)
                chart_type = "line"

            elif len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
                # Categorical + Numeric: Bar chart
                fig = self._create_bar_chart(df, categorical_cols[0], numeric_cols[0], title)
                chart_type = "bar"

            elif len(numeric_cols) >= 2:
                # Two numeric columns: Scatter plot
                fig = self._create_scatter_chart(df, numeric_cols[0], numeric_cols[1], title)
                chart_type = "scatter"

            elif len(numeric_cols) == 1:
                # Single numeric column: Histogram
                fig = self._create_histogram(df, numeric_cols[0], title)
                chart_type = "histogram"

            else:
                # No numeric data - can't make a meaningful chart
                logger.info("No numeric columns found - no chart created")
                chart_type = "none"

            # Track result
            if self.enable_tracing:
                langfuse_context.update_current_observation(
                    metadata={
                        "chart_type": chart_type,
                        "numeric_cols": len(numeric_cols),
                        "datetime_cols": len(datetime_cols),
                        "categorical_cols": len(categorical_cols),
                    }
                )

            logger.info(f"Created {chart_type} chart")
            return (fig, chart_type)

        except Exception as e:
            error_msg = f"Error creating chart: {e}"
            logger.error(error_msg, exc_info=True)
            if self.enable_tracing:
                langfuse_context.update_current_observation(
                    metadata={"error": str(e), "chart_type": "error"}
                )
            # Return None instead of raising - charts are optional
            return (None, "error")

    def _create_line_chart(
        self,
        df: pd.DataFrame,
        x_col: str,
        y_col: str,
        title: Optional[str] = None
    ) -> plt.Figure:
        """Create a line chart for time series data.

        Args:
            df: DataFrame with data
            x_col: Column name for X-axis (datetime)
            y_col: Column name for Y-axis (numeric)
            title: Optional chart title

        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        # Sort by datetime for proper line chart
        df_sorted = df.sort_values(by=x_col)

        # Create line plot
        sns.lineplot(data=df_sorted, x=x_col, y=y_col, marker='o', ax=ax)

        # Styling
        ax.set_title(title or f"{y_col} over {x_col}", fontsize=14, fontweight='bold')
        ax.set_xlabel(x_col.replace('_', ' ').title(), fontsize=12)
        ax.set_ylabel(y_col.replace('_', ' ').title(), fontsize=12)
        ax.grid(True, alpha=0.3)

        # Rotate x-axis labels if datetime
        plt.xticks(rotation=45, ha='right')

        plt.tight_layout()
        return fig

    def _create_bar_chart(
        self,
        df: pd.DataFrame,
        x_col: str,
        y_col: str,
        title: Optional[str] = None
    ) -> plt.Figure:
        """Create a bar chart for categorical + numeric data.

        Args:
            df: DataFrame with data
            x_col: Column name for X-axis (categorical)
            y_col: Column name for Y-axis (numeric)
            title: Optional chart title

        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        # Limit to top N categories if too many
        max_categories = 20
        if len(df) > max_categories:
            logger.info(f"Too many categories ({len(df)}), showing top {max_categories}")
            # Sort by y_col and take top N
            df_plot = df.nlargest(max_categories, y_col)
        else:
            df_plot = df

        # Create bar plot
        sns.barplot(data=df_plot, x=x_col, y=y_col, ax=ax)

        # Styling
        ax.set_title(title or f"{y_col} by {x_col}", fontsize=14, fontweight='bold')
        ax.set_xlabel(x_col.replace('_', ' ').title(), fontsize=12)
        ax.set_ylabel(y_col.replace('_', ' ').title(), fontsize=12)
        ax.grid(True, alpha=0.3, axis='y')

        # Rotate x-axis labels if needed
        if len(df_plot) > 5:
            plt.xticks(rotation=45, ha='right')

        plt.tight_layout()
        return fig

    def _create_scatter_chart(
        self,
        df: pd.DataFrame,
        x_col: str,
        y_col: str,
        title: Optional[str] = None
    ) -> plt.Figure:
        """Create a scatter plot for two numeric columns.

        Args:
            df: DataFrame with data
            x_col: Column name for X-axis (numeric)
            y_col: Column name for Y-axis (numeric)
            title: Optional chart title

        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        # Create scatter plot with regression line
        sns.regplot(data=df, x=x_col, y=y_col, ax=ax, scatter_kws={'alpha': 0.6})

        # Styling
        ax.set_title(title or f"{y_col} vs {x_col}", fontsize=14, fontweight='bold')
        ax.set_xlabel(x_col.replace('_', ' ').title(), fontsize=12)
        ax.set_ylabel(y_col.replace('_', ' ').title(), fontsize=12)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    def _create_histogram(
        self,
        df: pd.DataFrame,
        col: str,
        title: Optional[str] = None
    ) -> plt.Figure:
        """Create a histogram for a single numeric column.

        Args:
            df: DataFrame with data
            col: Column name (numeric)
            title: Optional chart title

        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        # Create histogram
        sns.histplot(data=df, x=col, bins=30, kde=True, ax=ax)

        # Styling
        ax.set_title(title or f"Distribution of {col}", fontsize=14, fontweight='bold')
        ax.set_xlabel(col.replace('_', ' ').title(), fontsize=12)
        ax.set_ylabel("Count", fontsize=12)
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        return fig

    def get_chart_recommendation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze DataFrame and recommend chart type without creating it.

        Args:
            df: DataFrame to analyze

        Returns:
            Dict with chart recommendation:
                - recommended_type: Type of chart recommended
                - confidence: 0.0-1.0 confidence in recommendation
                - reason: Explanation for recommendation
                - x_col: Recommended X-axis column
                - y_col: Recommended Y-axis column
        """
        if df is None or len(df) == 0:
            return {
                "recommended_type": "none",
                "confidence": 1.0,
                "reason": "DataFrame is empty",
                "x_col": None,
                "y_col": None,
            }

        # Convert Decimal columns to float for proper detection
        from decimal import Decimal
        for col in df.columns:
            if len(df) > 0 and isinstance(df[col].iloc[0], Decimal):
                df[col] = df[col].astype(float)

        # Analyze DataFrame structure
        numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32', 'number']).columns.tolist()
        datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()

        # Decision logic
        if len(datetime_cols) >= 1 and len(numeric_cols) >= 1:
            return {
                "recommended_type": "line",
                "confidence": 0.9,
                "reason": "Time series data detected (datetime + numeric columns)",
                "x_col": datetime_cols[0],
                "y_col": numeric_cols[0],
            }

        elif len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
            return {
                "recommended_type": "bar",
                "confidence": 0.8,
                "reason": "Categorical and numeric data detected",
                "x_col": categorical_cols[0],
                "y_col": numeric_cols[0],
            }

        elif len(numeric_cols) >= 2:
            return {
                "recommended_type": "scatter",
                "confidence": 0.7,
                "reason": "Two or more numeric columns detected",
                "x_col": numeric_cols[0],
                "y_col": numeric_cols[1],
            }

        elif len(numeric_cols) == 1:
            return {
                "recommended_type": "histogram",
                "confidence": 0.9,
                "reason": "Single numeric column detected",
                "x_col": numeric_cols[0],
                "y_col": None,
            }

        else:
            return {
                "recommended_type": "none",
                "confidence": 1.0,
                "reason": "No numeric columns found - table view only",
                "x_col": None,
                "y_col": None,
            }
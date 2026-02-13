# Copyright 2026 Ioannis Roumeliotis
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import pandas as pd
import lzma
import gzip
import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional

from file_organizer.analyzers.base import BaseAnalyzer
from file_organizer.core.models import (
    FileInfo,
    AnalysisResult,
    TabularAnalysis,
    ContentType
)


class TabularAnalyzer(BaseAnalyzer):
    """Analyzer for tabular data files (CSV, Excel, Parquet, etc.)"""
    
    supported_content_types = [ContentType.TABULAR]
    name = "tabular"
    
    def analyze(
        self,
        file_info: FileInfo,
        ai_provider=None
    ) -> AnalysisResult:
        """Analyze a tabular data file."""
        
        try:
            # Read the file based on extension
            df = self._read_file(file_info.path, file_info.name)
            
            # Calculate statistics
            missing_values = df.isnull().sum().to_dict()
            missing_percentage = {
                col: (missing_values[col] / len(df) * 100) if len(df) > 0 else 0
                for col in df.columns
            }
            
            # Numeric summary
            numeric_cols = df.select_dtypes(include=['number']).columns
            numeric_summary = None
            if len(numeric_cols) > 0:
                numeric_summary = {}
                for col in numeric_cols[:10]:  # Limit to first 10 numeric columns
                    numeric_summary[col] = {
                        "min": float(df[col].min()) if pd.notna(df[col].min()) else None,
                        "max": float(df[col].max()) if pd.notna(df[col].max()) else None,
                        "mean": float(df[col].mean()) if pd.notna(df[col].mean()) else None,
                        "std": float(df[col].std()) if pd.notna(df[col].std()) else None,
                    }
            
            # Sample values
            sample_values = {}
            for col in df.columns[:20]:  # Limit to first 20 columns
                sample_values[col] = df[col].head(5).tolist()
            
            # Memory usage
            memory_bytes = df.memory_usage(deep=True).sum()
            if memory_bytes < 1024:
                memory_str = f"{memory_bytes} B"
            elif memory_bytes < 1024 * 1024:
                memory_str = f"{memory_bytes / 1024:.1f} KB"
            else:
                memory_str = f"{memory_bytes / (1024 * 1024):.1f} MB"
            
            # Create tabular analysis
            tabular_analysis = TabularAnalysis(
                row_count=len(df),
                column_count=len(df.columns),
                columns=list(df.columns),
                dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
                missing_values=missing_values,
                missing_percentage=missing_percentage,
                memory_usage=memory_str,
                numeric_summary=numeric_summary,
                sample_values=sample_values
            )
            
            # Generate AI description if provider available
            ai_description = None
            if ai_provider:
                ai_description = self._generate_ai_description(
                    file_info, tabular_analysis, ai_provider
                )
            
            return AnalysisResult(
                file_info=file_info,
                analysis_type="tabular",
                analyzed_at=datetime.now(),
                tabular=tabular_analysis,
                ai_description=ai_description
            )
            
        except Exception as e:
            return AnalysisResult(
                file_info=file_info,
                analysis_type="tabular",
                analyzed_at=datetime.now(),
                error=str(e)
            )
    
    def _read_file(self, path: Path, filename: str) -> pd.DataFrame:
        """Read tabular file based on extension, handling compression."""
        
        filename_lower = filename.lower()
        
        # Handle double extensions for compression
        # e.g., .pkl.xz, .csv.gz, .pkl.gz
        
        # .pkl.xz - LZMA compressed pickle
        if filename_lower.endswith('.pkl.xz') or filename_lower.endswith('.pickle.xz'):
            with lzma.open(path, 'rb') as f:
                data = pickle.load(f)
            return self._to_dataframe(data)
        
        # .pkl.gz - Gzip compressed pickle
        if filename_lower.endswith('.pkl.gz') or filename_lower.endswith('.pickle.gz'):
            with gzip.open(path, 'rb') as f:
                data = pickle.load(f)
            return self._to_dataframe(data)
        
        # .csv.gz - Gzip compressed CSV
        if filename_lower.endswith('.csv.gz'):
            return pd.read_csv(path, compression='gzip', nrows=10000)
        
        # .csv.xz - LZMA compressed CSV
        if filename_lower.endswith('.csv.xz'):
            return pd.read_csv(path, compression='xz', nrows=10000)
        
        # .json.gz - Gzip compressed JSON
        if filename_lower.endswith('.json.gz'):
            return pd.read_json(path, compression='gzip')
        
        # Standard extensions
        ext = path.suffix.lower()
        
        if ext == ".csv":
            return pd.read_csv(path, nrows=10000)
        elif ext in [".xlsx", ".xls"]:
            return pd.read_excel(path, nrows=10000)
        elif ext == ".parquet":
            return pd.read_parquet(path)
        elif ext in [".pkl", ".pickle"]:
            data = pd.read_pickle(path)
            return self._to_dataframe(data)
        elif ext == ".json":
            return pd.read_json(path)
        elif ext == ".tsv":
            return pd.read_csv(path, sep="\t", nrows=10000)
        elif ext == ".feather":
            return pd.read_feather(path)
        elif ext == ".h5" or ext == ".hdf5":
            return pd.read_hdf(path)
        elif ext == ".xz":
            # Standalone .xz - try to detect content
            with lzma.open(path, 'rb') as f:
                try:
                    data = pickle.load(f)
                    return self._to_dataframe(data)
                except:
                    # Try reading as CSV
                    f.seek(0)
                    return pd.read_csv(f, nrows=10000)
        elif ext == ".gz":
            # Standalone .gz - try to detect content
            with gzip.open(path, 'rb') as f:
                try:
                    data = pickle.load(f)
                    return self._to_dataframe(data)
                except:
                    f.seek(0)
                    return pd.read_csv(f, nrows=10000)
        else:
            # Try CSV as fallback
            return pd.read_csv(path, nrows=10000)
    
    def _to_dataframe(self, data) -> pd.DataFrame:
        """Convert various data types to DataFrame."""
        
        if isinstance(data, pd.DataFrame):
            return data
        elif isinstance(data, pd.Series):
            return data.to_frame()
        elif isinstance(data, dict):
            # Try to convert dict to DataFrame
            try:
                return pd.DataFrame(data)
            except:
                # If dict of non-tabular data, create single-row DataFrame
                return pd.DataFrame([data])
        elif isinstance(data, list):
            return pd.DataFrame(data)
        else:
            # Last resort - create single-value DataFrame
            return pd.DataFrame({'data': [str(data)]})
    
    def _generate_ai_description(
        self,
        file_info: FileInfo,
        analysis: TabularAnalysis,
        ai_provider
    ) -> Optional[str]:
        """Generate AI description of the dataset."""
        
        from file_organizer.prompts.analysis import build_tabular_analysis_prompt, ANALYSIS_SYSTEM_PROMPT
        
        prompt = build_tabular_analysis_prompt(file_info, analysis)
        
        try:
            messages = [
                ("system", ANALYSIS_SYSTEM_PROMPT),
                ("user", prompt),
            ]
            response = ai_provider.base_llm.invoke(messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"Could not generate AI description: {str(e)}"
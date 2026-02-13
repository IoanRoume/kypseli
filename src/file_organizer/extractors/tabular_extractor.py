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
from file_organizer.extractors.base import BaseExtractor
from file_organizer.core.models import FileInfo, ExtractedContent

import pandas as pd


class TabularExtractor(BaseExtractor):
    supported_extensions = [
        ".csv", ".tsv",
        ".xlsx", ".xls", ".ods",
        ".parquet", ".feather", ".orc",
        ".pkl", ".h5", ".xz",
        ".dta", ".sas7bdat"
    ]


    def extract(self, file_info: FileInfo, max_chars: int = 7000) -> ExtractedContent:
        file_path = file_info.path
        ext = file_path.suffix.lower()

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            if ext in ['.csv', '.txt', '.xz', '.gz']:
                df = pd.read_csv(file_path, nrows=20)
            
            elif ext == '.tsv':
                df = pd.read_csv(file_path, sep='\t', nrows=20)
                
            elif ext in ['.xlsx', '.xls', '.ods']:
                df = pd.read_excel(file_path, nrows=20)
                
            elif ext == '.sas7bdat':
                df = pd.read_sas(file_path)
                df = df.head(20)

            elif ext in ['.parquet']:
                df = pd.read_parquet(file_path)
                df = df.head(20)
                
            elif ext in ['.feather']:
                df = pd.read_feather(file_path)
                df = df.head(20)
                
            elif ext in ['.pkl', '.pickle', '.xz']:
                df = pd.read_pickle(file_path)
                if not isinstance(df, pd.DataFrame):
                    df = pd.DataFrame(df)
                df = df.head(20)

            elif ext in ['.h5', '.hdf5']:

                with pd.HDFStore(file_path, mode='r') as store:
                    keys = store.keys()
                    if keys:
                        df = store.select(keys[0], stop=20)
                    else:
                        df = pd.DataFrame()

            elif ext == '.orc':
                df = pd.read_orc(file_path)
                df = df.head(20)
                
            elif ext == '.dta':
                df = pd.read_stata(file_path)
                df = df.head(20)

            else:
                df = pd.read_csv(file_path, nrows=20)

        except Exception as e:
            return ExtractedContent(
                file_info=file_info,
                content=f"Error extracting tabular data: {str(e)}",
                extraction_method="failed"
            )

        content = df.to_string()[:max_chars]
        
        return ExtractedContent(
            file_info=file_info,
            content=content,
            extraction_method="first_20_rows"
        )


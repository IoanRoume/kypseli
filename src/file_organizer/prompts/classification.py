from file_organizer.core.models import ExtractedContent, FoldersToClassify

SYSTEM_PROMPT = """You are a file organization assistant. Your task is to classify files into the most appropriate folder based on the file's metadata and content.

You will receive:
1. Information about a file (name, extension, size, content type, creation date, and a preview of its content)
2. A list of available folders with optional descriptions

Your job is to determine which folder is the best match for the file.

Rules:
- Choose the single most appropriate folder from the provided list
- If a folder has a description, use it to guide your decision
- If no description exists, infer the folder's purpose from its name
- Provide a confidence score from 0.0 to 1.0
- Keep your reasoning brief and clear

You must respond with valid JSON only. No additional text, no markdown formatting, no code blocks. Just the raw JSON object."""


def build_classification_prompt(
    extracted_content: ExtractedContent,
    folders_to_classify: FoldersToClassify
) -> str:
    
    file_info = extracted_content.file_info
    
    # Build folder list string
    folder_descriptions = []
    for folder in folders_to_classify.folders:
        if folder.description:
            folder_descriptions.append(f"- {folder.folder_path.name}: {folder.description}")
        else:
            folder_descriptions.append(f"- {folder.folder_path.name}: (no description provided)")
    
    folders_str = "\n".join(folder_descriptions)
    
    # Format file size
    size_bytes = file_info.size
    if size_bytes < 1024:
        size_str = f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        size_str = f"{size_bytes / 1024:.1f} KB"
    else:
        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
    
    prompt = f"""Classify the following file into one of the available folders.

FILE INFORMATION:
- Name: {file_info.name}
- Extension: {file_info.extension}
- Size: {size_str}
- Content type: {file_info.content_type.value}
- Date created: {file_info.date_created.strftime("%Y-%m-%d %H:%M:%S")}

CONTENT PREVIEW:
{extracted_content.content}

AVAILABLE FOLDERS:
{folders_str}

Respond with this exact JSON structure:
{{
    "folder_name": "chosen folder name from the list above",
    "confidence": 0.0,
    "reasoning": "brief explanation of why this folder was chosen"
}}"""

    return prompt
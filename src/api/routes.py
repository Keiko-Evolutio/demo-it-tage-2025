# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license.
# See LICENSE file in the project root for full license information.
import json
import logging
import os
from typing import Dict

import fastapi
from fastapi import Request, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from azure.ai.inference.prompts import PromptTemplate
from azure.ai.inference.aio import ChatCompletionsClient

from .util import get_logger, ChatRequest
from .search_index_manager import SearchIndexManager
from .blob_storage_manager import BlobStorageManager
from .document_processor import DocumentProcessor
from azure.core.exceptions import HttpResponseError


from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Optional
import secrets

security = HTTPBasic()


username = os.getenv("WEB_APP_USERNAME")
password = os.getenv("WEB_APP_PASSWORD")
basic_auth = username and password

def authenticate(credentials: Optional[HTTPBasicCredentials] = Depends(security)) -> None:

    if not basic_auth:
        logger.info("Skipping authentication: WEB_APP_USERNAME or WEB_APP_PASSWORD not set.")
        return
    
    correct_username = secrets.compare_digest(credentials.username, username)
    correct_password = secrets.compare_digest(credentials.password, password)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return

auth_dependency = Depends(authenticate) if basic_auth else None

logger = get_logger(
    name="azureaiapp_routes",
    log_level=logging.INFO,
    log_file_name=os.getenv("APP_LOG_FILE"),
    log_to_console=True
)

router = fastapi.APIRouter()
templates = Jinja2Templates(directory="api/templates")


# Accessors to get app state
def get_chat_client(request: Request) -> ChatCompletionsClient:
    return request.app.state.chat


def get_chat_model(request: Request) -> str:
    return request.app.state.chat_model


def get_search_index_namager(request: Request) -> SearchIndexManager:
    return request.app.state.search_index_manager


def get_blob_storage_manager(request: Request) -> BlobStorageManager:
    return request.app.state.blob_storage_manager


def serialize_sse_event(data: Dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.get("/", response_class=HTMLResponse)
async def index_name(request: Request, _ = auth_dependency):
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request,
        }
    )

@router.post("/chat")
async def chat_stream_handler(
    chat_request: ChatRequest,
    chat_client: ChatCompletionsClient = Depends(get_chat_client),
    model_deployment_name: str = Depends(get_chat_model),
    search_index_manager: SearchIndexManager = Depends(get_search_index_namager),
    blob_storage_manager: BlobStorageManager = Depends(get_blob_storage_manager),
    _ = auth_dependency
) -> fastapi.responses.StreamingResponse:
    
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "text/event-stream"
    }    
    if chat_client is None:
        raise Exception("Chat client not initialized")

    async def response_stream():
        messages = [{"role": message.role, "content": message.content} for message in chat_request.messages]

        prompt_messages = PromptTemplate.from_string('You are a helpful assistant').create_messages()
        sources = []
        # Use RAG model, only if we were provided index and we have found a context there.
        if search_index_manager is not None:
            context, sources = await search_index_manager.search(chat_request)

            # Generate SAS URLs for sources if blob storage manager is available
            if sources and blob_storage_manager is not None:
                for source in sources:
                    if 'url' in source and source['url']:
                        # Extract blob name from URL
                        blob_name = source['url'].split('/')[-1]
                        # Remove query parameters if any
                        blob_name = blob_name.split('?')[0]
                        try:
                            # Generate SAS URL with 24-hour expiry
                            sas_url = await blob_storage_manager.generate_sas_url(blob_name, expiry_hours=24)

                            # Add page number fragment if available
                            if source.get('page_number') is not None:
                                sas_url += f"#page={source['page_number']}"

                            source['url'] = sas_url
                        except Exception as e:
                            logger.error(f"Error generating SAS URL for {blob_name}: {e}")

            if context:
                prompt_messages = PromptTemplate.from_string(
                    'You are a helpful assistant that answers some questions '
                    'with the help of some context data.\n\nHere is '
                    'the context data:\n\n{{context}}').create_messages(data=dict(context=context))
                logger.info(f"{prompt_messages=}")
            else:
                logger.info("Unable to find the relevant information in the index for the request.")
        try:
            accumulated_message = ""
            chat_coroutine = await chat_client.complete(
                model=model_deployment_name, messages=prompt_messages + messages, stream=True
            )
            async for event in chat_coroutine:
                if event.choices:
                    first_choice = event.choices[0]
                    if first_choice.delta.content:
                        message = first_choice.delta.content
                        accumulated_message += message
                        yield serialize_sse_event({
                                        "content": message,
                                        "type": "message",
                                    }
                                )

            # Send completed message with sources
            yield serialize_sse_event({
                "content": accumulated_message,
                "type": "completed_message",
                "sources": sources
            })
        except BaseException as e:
            error_processed = False
            response = "There is an error!"
            try:
                if '(content_filter)' in e.args[0]:
                    rai_dict = e.response.json()['error']['innererror']['content_filter_result']
                    errors = []
                    for k, v in rai_dict.items():
                        if v['filtered']:
                            if 'severity' in v:
                                errors.append(f"{k}, severity: {v['severity']}")
                            else:
                                errors.append(k)
                    error_text = f"We have found the next safety issues in the response: {', '.join(errors)}"
                    logger.error(error_text)
                    response = error_text
                    error_processed = True
            except BaseException:
                pass
            if not error_processed:
                error_text = str(e)
                logger.error(error_text)
                response = error_text
            yield serialize_sse_event({
                            "content": response,
                            "type": "completed_message",
                        })
        yield serialize_sse_event({
            "type": "stream_end"
            })

    return StreamingResponse(response_stream(), headers=headers)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    search_index_manager: SearchIndexManager = Depends(get_search_index_namager),
    blob_storage_manager: BlobStorageManager = Depends(get_blob_storage_manager),
    _ = auth_dependency
) -> JSONResponse:
    """
    Upload and process a document for RAG.

    Steps:
    1. Validate file format
    2. Extract text from document
    3. Upload to blob storage
    4. Chunk text
    5. Generate embeddings and index
    """
    try:
        # Check if RAG is enabled
        if search_index_manager is None or blob_storage_manager is None:
            return JSONResponse(
                status_code=400,
                content={"error": "RAG functionality is not enabled"}
            )

        # Validate file format
        if not DocumentProcessor.is_supported(file.filename):
            return JSONResponse(
                status_code=400,
                content={"error": f"Unsupported file format. Supported: {', '.join(DocumentProcessor.SUPPORTED_EXTENSIONS)}"}
            )

        # Read file content
        file_content = await file.read()

        # Extract text from document with page mapping
        logger.info(f"Extracting text from {file.filename}")
        text, char_to_page = await DocumentProcessor.extract_text(file_content, file.filename)

        if not text.strip():
            return JSONResponse(
                status_code=400,
                content={"error": "No text could be extracted from the document"}
            )

        # Upload to blob storage
        logger.info(f"Uploading {file.filename} to blob storage")
        blob_url = await blob_storage_manager.upload_document(
            filename=file.filename,
            file_content=file_content,
            metadata={"original_filename": file.filename}
        )

        # Chunk text with page number tracking
        logger.info(f"Chunking text from {file.filename}")
        chunks = await DocumentProcessor.chunk_text(text, char_to_page, sentences_per_chunk=4)

        if not chunks:
            return JSONResponse(
                status_code=400,
                content={"error": "No chunks could be created from the document"}
            )

        # Upload chunks to search index
        logger.info(f"Indexing {len(chunks)} chunks from {file.filename}")
        await search_index_manager.upload_document_chunks(
            chunks=chunks,
            source_document=file.filename,
            source_url=blob_url
        )

        logger.info(f"Successfully processed {file.filename}")

        return JSONResponse(
            status_code=200,
            content={
                "message": "Document uploaded and indexed successfully",
                "filename": file.filename,
                "chunks_count": len(chunks),
                "blob_url": blob_url
            }
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to process document: {str(e)}"}
        )

# db/__init__.py
from .database import (
    init_database,
    create_session,
    get_all_sessions,
    save_message,
    get_session_messages,
    save_file_metadata,
    mark_file_processed,
    get_session_files,
    check_session_has_files,
    delete_session
)

from .vector_store import (
    get_or_create_collection,
    add_document_chunks,
    query_relevant_chunks,
    delete_session_collection
)

__all__ = [
    'init_database',
    'create_session',
    'get_all_sessions',
    'save_message',
    'get_session_messages',
    'save_file_metadata',
    'mark_file_processed',
    'get_session_files',
    'check_session_has_files',
    'delete_session',
    'get_or_create_collection',
    'add_document_chunks',
    'query_relevant_chunks',
    'delete_session_collection'
]
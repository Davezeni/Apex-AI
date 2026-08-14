-- Apex AI - Supabase schema (run once in the Supabase SQL editor).
-- Creates the tables backing conversations, messages, and the knowledge base.
-- Pure ASCII only; standard Postgres types.

create table if not exists conversations (
  id text primary key,
  title text not null,
  created_at double precision not null,
  updated_at double precision not null
);

create table if not exists messages (
  id text primary key,
  conversation_id text not null references conversations(id) on delete cascade,
  role text not null,
  kind text not null,
  content text not null,
  created_at double precision not null
);

create index if not exists messages_conv_idx
  on messages(conversation_id, created_at);

create table if not exists knowledge_chunks (
  id text primary key,
  document_id text not null,
  source text not null,
  chunk_index integer not null,
  chunk_text text not null,
  embedding text not null
);

create index if not exists knowledge_doc_idx
  on knowledge_chunks(document_id);

create table if not exists workspace_files (
  path text primary key,
  content text not null,
  updated_at double precision not null
);

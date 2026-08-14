-- Apex AI — Supabase schema (run once in Supabase SQL editor).
-- Creates the tables backing conversations, messages, and the knowledge base.

create table if not exists conversations (
  id text primary key,
  title text not null,
  created_at float8 not null,
  updated_at float8 not null
);

create table if not exists messages (
  id text primary key,
  conversation_id text not null references conversations(id) on delete cascade,
  role text not null,
  kind text not null,
  content text not null,
  created_at float8 not null
);

create index if not exists messages_conv_idx on messages(conversation_id, created_at);

create table if not exists knowledge_chunks (
  id text primary key,
  document_id text not null,
  source text not null,
  chunk_index int not null,
  text text not null,
  embedding text not null
);

create index if not exists knowledge_doc_idx on knowledge_chunks(document_id);

-- The backend uses the service_role key (bypasses RLS), so no policies are
-- required. If you later switch to the anon key, add RLS policies here.

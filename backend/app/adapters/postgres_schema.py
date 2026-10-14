"""Tables the live chat path writes. Created if missing. Nothing is dropped."""

SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS sessions (
      id UUID PRIMARY KEY,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chats (
      id UUID PRIMARY KEY,
      session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS messages (
      id UUID PRIMARY KEY,
      chat_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
      role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
      content TEXT NOT NULL,
      intent TEXT,
      language TEXT,
      tax_year TEXT,
      sources JSONB,
      answer_source TEXT,
      confidence TEXT,
      verified BOOLEAN,
      model TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS messages_chat_id_created_at_idx ON messages (chat_id, created_at)",
    """
    CREATE TABLE IF NOT EXISTS feedback (
      id UUID PRIMARY KEY,
      message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
      rating TEXT NOT NULL CHECK (rating IN ('up', 'down')),
      reason TEXT,
      comment TEXT,
      share_conversation BOOLEAN NOT NULL DEFAULT false,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sections (
      parent_id TEXT PRIMARY KEY,
      doc_id TEXT NOT NULL,
      section TEXT,
      section_title TEXT,
      page_start INT,
      page_end INT,
      text TEXT NOT NULL,
      corpus_version TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS sections_doc_id_idx ON sections (doc_id)",
    """
    CREATE TABLE IF NOT EXISTS meta (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS checklists (
      id UUID PRIMARY KEY,
      session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
      template_id TEXT NOT NULL,
      answers JSONB NOT NULL,
      steps JSONB NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS experts (
      id UUID PRIMARY KEY,
      name TEXT NOT NULL,
      firm TEXT,
      city TEXT NOT NULL,
      specialties TEXT[] NOT NULL,
      profile_url TEXT NOT NULL,
      source TEXT NOT NULL,
      last_updated DATE NOT NULL,
      active BOOLEAN NOT NULL DEFAULT true,
      UNIQUE (source, profile_url)
    )
    """,
    "CREATE INDEX IF NOT EXISTS experts_city_idx ON experts (city)",
    "CREATE INDEX IF NOT EXISTS experts_specialties_idx ON experts USING GIN (specialties)",
    """
    CREATE TABLE IF NOT EXISTS notifications (
      id UUID PRIMARY KEY,
      sha256 TEXT NOT NULL UNIQUE,
      title TEXT NOT NULL,
      doc_type TEXT NOT NULL,
      domain TEXT,
      source_url TEXT NOT NULL,
      published_at DATE,
      effective_from DATE,
      summary TEXT NOT NULL,
      who_is_affected TEXT,
      key_changes TEXT[],
      indexed BOOLEAN NOT NULL DEFAULT false,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS notifications_published_idx ON notifications (published_at DESC)",
    """
    CREATE TABLE IF NOT EXISTS web_pages (
      id UUID PRIMARY KEY,
      url TEXT NOT NULL UNIQUE,
      site TEXT NOT NULL,
      title TEXT,
      content_type TEXT NOT NULL,
      sha256 TEXT NOT NULL,
      first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      removed BOOLEAN NOT NULL DEFAULT false,
      chunk_count INT NOT NULL DEFAULT 0
    )
    """,
    "CREATE INDEX IF NOT EXISTS web_pages_site_idx ON web_pages (site)",
    """
    CREATE TABLE IF NOT EXISTS crawl_runs (
      id UUID PRIMARY KEY,
      site TEXT NOT NULL,
      started_at TIMESTAMPTZ NOT NULL,
      finished_at TIMESTAMPTZ,
      pages_fetched INT NOT NULL DEFAULT 0,
      pages_new INT NOT NULL DEFAULT 0,
      pages_changed INT NOT NULL DEFAULT 0,
      pages_removed INT NOT NULL DEFAULT 0,
      success BOOLEAN,
      error TEXT
    )
    """,
)

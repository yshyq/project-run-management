CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- This schema targets PostgreSQL 18 and remains compatible with PostgreSQL 15+.
-- SQLAlchemy creates tables automatically at startup; this file is for DBA review.

CREATE TABLE IF NOT EXISTS departments (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  name varchar(100) UNIQUE NOT NULL,
  parent_id uuid REFERENCES departments(id),
  default_permissions jsonb NOT NULL DEFAULT '[]',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  username varchar(80) UNIQUE NOT NULL,
  name varchar(100) NOT NULL,
  password_hash varchar(255) NOT NULL,
  mobile varchar(30),
  title varchar(100),
  department_id uuid REFERENCES departments(id),
  is_active boolean NOT NULL DEFAULT true,
  is_superuser boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS projects (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  customer_name varchar(200) NOT NULL,
  remote_method varchar(200),
  server_ip varchar(120),
  server_account varchar(120),
  server_password text,
  login_url varchar(500),
  login_account varchar(120),
  login_password text,
  database_url varchar(500),
  database_account varchar(120),
  database_password text,
  other_info text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS permission_requests (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  requester_id uuid NOT NULL REFERENCES users(id),
  project_id uuid NOT NULL REFERENCES projects(id),
  permission_scope varchar(40) NOT NULL,
  reason text NOT NULL,
  status varchar(20) NOT NULL DEFAULT 'pending',
  approver_id uuid REFERENCES users(id),
  approved_permissions jsonb NOT NULL DEFAULT '[]',
  created_at timestamptz NOT NULL DEFAULT now(),
  decided_at timestamptz
);

CREATE TABLE IF NOT EXISTS workflows (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  name varchar(120) UNIQUE NOT NULL,
  description text,
  is_default boolean NOT NULL DEFAULT false,
  steps jsonb NOT NULL DEFAULT '[]',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS project_supports (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id uuid NOT NULL REFERENCES projects(id),
  requester_id uuid NOT NULL REFERENCES users(id),
  workflow_id uuid NOT NULL REFERENCES workflows(id),
  support_type varchar(50) NOT NULL,
  priority varchar(20) NOT NULL DEFAULT '普通',
  title varchar(200) NOT NULL,
  description text NOT NULL,
  current_step varchar(80) NOT NULL DEFAULT 'delivery',
  status varchar(20) NOT NULL DEFAULT 'open',
  assignee_id uuid REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS support_action_logs (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  support_id uuid NOT NULL REFERENCES project_supports(id),
  actor_id uuid NOT NULL REFERENCES users(id),
  action varchar(80) NOT NULL,
  from_step varchar(80),
  to_step varchar(80),
  comment text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  actor_id uuid REFERENCES users(id),
  action varchar(120) NOT NULL,
  target_type varchar(80) NOT NULL,
  target_id varchar(120),
  detail jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

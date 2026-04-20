-- +goose Up
-- +goose StatementBegin
SELECT 'up SQL query';
create table if not exists fields
(
    id              uuid                     default gen_random_uuid() not null primary key,
    organization_id uuid references organizations (id)                 not null,
    name            varchar(100)                                       not null,
    description     varchar(200)                                       not null,
    created_at      timestamp with time zone default now(),
    updated_at      timestamp with time zone default now()
);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
SELECT 'down SQL query';
drop table if exists fields;
-- +goose StatementEnd


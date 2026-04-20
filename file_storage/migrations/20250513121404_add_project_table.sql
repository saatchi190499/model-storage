-- +goose Up
-- +goose StatementBegin
SELECT 'up SQL query';
create table if not exists projects
(
    id          uuid                     default gen_random_uuid() not null primary key,
    field_id     uuid references fields (id)                         not null,
    name        varchar(100)                                       not null,
    description varchar(200)                                       not null,
    is_private  bool                     default false,
    created_at  timestamp with time zone default now(),
    updated_at  timestamp with time zone default now()
);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
SELECT 'down SQL query';
drop table if exists projects;
-- +goose StatementEnd



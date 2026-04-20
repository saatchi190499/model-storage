-- +goose Up
-- +goose StatementBegin
SELECT 'up SQL query';
create table if not exists commits
(
    id               serial                        not null primary key,
    project_id       uuid references projects (id) not null,
    user_id          uuid                          not null,
    message          varchar(255)                  not null,
    parent_commit_id int                           references commits (id) on delete set null,
    is_complete      bool                     default false,
    created_at       timestamp with time zone default now(),
    updated_at       timestamp with time zone default now()
);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
SELECT 'down SQL query';
drop table if exists commits;
-- +goose StatementEnd

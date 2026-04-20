-- +goose Up
-- +goose StatementBegin
SELECT 'up SQL query';
create table if not exists file_versions
(
    id          serial                      not null primary key,
    file_id     int references files (id)   not null,
    storage_key text,
    version     int                         not null,
    file_size   int                         not null,
    hash        text                        not null,
    commit_id   int references commits (id) not null,
    is_deleted  bool                     default false,
    created_at  timestamp with time zone default now(),
    updated_at  timestamp with time zone default now(),
    unique (file_id, version)
);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
SELECT 'down SQL query';
drop table if exists file_versions;
-- +goose StatementEnd

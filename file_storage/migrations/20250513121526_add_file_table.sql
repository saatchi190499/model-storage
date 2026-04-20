-- +goose Up
-- +goose StatementBegin
SELECT 'up SQL query';
create table if not exists files
(
    id                   serial                                  not null primary key,
    project_id           uuid references projects (id)           not null,
    last_file_version_id int                      default 0      not null,
    name                 varchar(100)                            not null,
    file_format          varchar(20)              default '.txt' not null,
    path                 text                                    not null,
    created_at           timestamp with time zone default now(),
    updated_at           timestamp with time zone default now()
);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
SELECT 'down SQL query';
drop table if exists files;
-- +goose StatementEnd

-- +goose Up
-- +goose StatementBegin
SELECT 'up SQL query';
create table if not exists field_members
(
    id      serial                     not null primary key,
    field_id uuid references fields (id) not null,
    user_id uuid                       not null,
    role_id int references roles (id)  not null
);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
SELECT 'down SQL query';
drop table if exists field_members;
-- +goose StatementEnd



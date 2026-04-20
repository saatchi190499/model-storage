-- +goose Up
-- +goose StatementBegin
SELECT 'up SQL query';
alter table fields
    add column is_deleted bool default false;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
SELECT 'down SQL query';
alter table fields
    drop column is_deleted;
-- +goose StatementEnd


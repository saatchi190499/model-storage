-- +goose Up
-- +goose StatementBegin
SELECT 'up SQL query';
alter table if exists fields
    drop constraint if exists fields_organization_id_fkey;

alter table if exists fields
    drop column if exists organization_id;

drop table if exists organizations;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
SELECT 'down SQL query';
create table if not exists organizations
(
    id          uuid                     default gen_random_uuid() not null primary key,
    name        varchar(200)                                       not null,
    description varchar(200)                                       not null,
    created_at  timestamp with time zone default now(),
    updated_at  timestamp with time zone default now(),
    is_deleted  bool                     default false
);

alter table if exists fields
    add column if not exists organization_id uuid;

with new_org as (
    insert into organizations (name, description, created_at, updated_at, is_deleted)
    values ('Default Organization', 'Generated during rollback migration', now(), now(), false)
    returning id
)
update fields
set organization_id = (select id from new_org)
where organization_id is null;

alter table if exists fields
    alter column organization_id set not null;

alter table if exists fields
    add constraint fields_organization_id_fkey
        foreign key (organization_id) references organizations (id);
-- +goose StatementEnd

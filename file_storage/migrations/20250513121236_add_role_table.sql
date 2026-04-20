-- +goose Up
-- +goose StatementBegin
SELECT 'up SQL query';
create table if not exists roles
(
    id          int primary key,
    name        varchar(50)  not null,
    scope       varchar(20)  not null check (scope in ('organization', 'project', 'field')),
    description varchar(200) not null
);

insert into roles (id, name, scope, description)
values ('1', 'owner', 'organization', 'Full control over the organization, including billing and user management.'),
       ('2', 'admin', 'organization', 'Can manage fields, projects, and users within the organization.'),
       ('3', 'member', 'organization', 'Default role for users; can join projects or fields if invited.'),
       ('4', 'maintainer', 'project', 'Admin for a project.'),
       ('5', 'developer', 'project', 'Full read/write access to project.'),
       ('6', 'reporter', 'project', 'Read access to project.'),
       ('7', 'owner', 'project', 'Full control of the project and all its settings'),
       ('8', 'maintainer', 'field', '	High-level management across all projects in the group.'),
       ('9', 'developer', 'field', 'Work on code and issues across all projects in the group.'),
       ('10', 'reporter', 'field', 'View code and activity across all group projects.'),
       ('11', 'owner', 'field', 'Full control of the group and all its settings');
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
SELECT 'down SQL query';
drop table if exists roles;
-- +goose StatementEnd


#!/usr/bin/env python

import os
import sys
import json
import pprint

npm_ls_output = []

# Expects input from `yarn list --json --no-progress`

for line in sys.stdin:
    npm_ls_output.append(line)

npm_ls_output = ''.join(npm_ls_output)
json_data = json.loads(npm_ls_output)


def clean_tree_list(trees, parent=None):
    key_whitelist = ['name', 'children']
    for tree in trees:
        for key in tree.keys():
            if key not in key_whitelist:
                del tree[key]
        if parent is not None:
            tree['parent'] = parent

        name_parts = tree['name'].split('@')
        if len(name_parts) == 3:
            more_name_parts = name_parts[1].split('/')
            tree['org'] = more_name_parts[0]
            tree['name'] = more_name_parts[1]
        else:
            tree['name'] = name_parts[0]
        tree['version'] = name_parts[len(name_parts) - 1]

        if 'children' in tree:
            clean_tree_list(tree['children'], tree)


def get_path_string(tree):
    if 'parent' in tree:
        return '{}--{}'.format(get_path_string(tree['parent']), tree['name'])
    else:
        return tree['name']


def get_module_path(module, org, hypothetical_node_modules, stop_at):
    if hypothetical_node_modules == stop_at:
        raise Exception('Could not find package {}'.format(module))

    if os.path.basename(hypothetical_node_modules) == 'node_modules' and os.path.isdir(hypothetical_node_modules):
        for entry in os.listdir(hypothetical_node_modules):
            if entry == module:
                return os.path.join(hypothetical_node_modules, module)

        if org is not None:
            org_dir = os.path.join(hypothetical_node_modules, '@{}'.format(org))
            if os.path.isdir(org_dir):
                for entry in os.listdir(org_dir):
                    if entry == module:
                        return os.path.join(org_dir, module)
    return get_module_path(module, org, os.path.dirname(hypothetical_node_modules), stop_at)


def resolve_unflattened_module_path(tree, root):
    if 'org' in tree:
        package_path = 'node_modules/@{}/{}'.format(tree['org'], tree['name'])
    else:
        package_path = 'node_modules/{}'.format(tree['name'])

    if 'parent' not in tree:
        return os.path.join(root, package_path)

    else:
        parent_path = resolve_unflattened_module_path(tree['parent'], root)
        return os.path.join(parent_path, package_path)


def resolve_flattened_path(module, tree):
    modules = os.path.dirname(tree['unflattened_node_modules'])
    if os.path.isdir(modules):
        for file in os.listdir(modules):
            if file == module:
                return os.path.join(modules, module)

    if 'parent' in tree:
        return resolve_flattened_path(module,  tree['parent'])


def resolve_unflattened_module_paths(trees, root):
    for tree in trees:
        tree['unflattened_node_modules'] = resolve_unflattened_module_path(tree, root)

        if 'children' in tree:
            resolve_unflattened_module_paths(tree['children'], root)


def resolve_flattened_paths(dependencies, stop_at):
    for entry in dependencies:
        if 'unflattened_node_modules' in entry:
            entry['path'] = resolve_flattened_path(entry['name'], entry)
        if 'parent' in entry:
            resolve_flattened_paths(entry['parent'], stop_at)


def remove_unflattened_node_modules(trees):
    for tree in trees:
        if 'unflattened_node_modules' in tree:
            del tree['unflattened_node_modules']
        if 'children' in tree:
            remove_unflattened_node_modules(tree['children'])


def verify_paths(trees):
    for tree in trees:
        try:
            if 'path' in tree:
                if tree['path'] is None:
                    raise Exception('Path for {} was None ({})'.format(get_path_string(tree), tree['unflattened_node_modules']))
                if not os.path.isdir(tree['path']):
                    raise Exception('Couldn\'t find {} from {}'.format(get_path_string(tree), tree['unflattened_node_modules']))
                if 'children' in tree:
                    verify_paths(tree['children'])
        except Exception as e:
            print(e)

dependencies = json_data['data']['trees']
clean_tree_list(dependencies)
resolve_unflattened_module_paths(dependencies, os.getcwd())
resolve_flattened_paths(dependencies, os.getcwd())
verify_paths(dependencies)
remove_unflattened_node_modules(dependencies)

pprint.pprint(dependencies)


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

            tree['org'] = more_name_parts[0]
            tree['name'] = more_name_parts[1]
        else:
            tree['name'] = name_parts[0]
        tree['version'] = name_parts[len(name_parts) - 1]

        if 'children' in tree:
            clean_tree_list(tree['children'], tree)


def get_qualified_name(tree):
    parent = tree['parent']
    name = tree['name']
    if 'parent' in tree:
        return '{}--{}'.format(get_qualified_name(parent, name))
    else:
        return tree['name']


def get_module_path(module, org, proposed_node_modules, stop_at):
    if proposed_node_modules == stop_at:
        raise Exception('Could not find package {}'.format(module))

    if os.path.basename(proposed_node_modules) == 'node_modules' \
       and os.path.isdir(proposed_node_modules):
        for entry in os.listdir(proposed_node_modules):
            if entry == module:
                return os.path.join(proposed_node_modules, module)

        if org is not None:
            org_dir = os.path.join(proposed_node_modules, '@{}'.format(org))
            if os.path.isdir(org_dir):
                for entry in os.listdir(org_dir):
                    if entry == module:
                        return os.path.join(org_dir, module)
    parent = os.path.dirname(proposed_node_modules)
    return get_module_path(module, org, parent, stop_at)


def resolve_flattened_path(module, tree, org):
    modules = os.path.dirname(tree['guessed_modules'])
    if os.path.isdir(modules):
        for file in os.listdir(modules):
            if file == module:
                return os.path.join(modules, module)

    if org is not None:
        modules = os.path.join(modules, '@{}'.format(org))
        if os.path.isdir(modules):
            for file in os.listdir(modules):
                if file == module:
                    return os.path.join(modules, module)

    if 'parent' in tree:
        return resolve_flattened_path(module,  tree['parent'])


def guess_module_path(tree, root):
    if 'org' in tree:
        package_path = 'node_modules/@{}/{}'.format(tree['org'], tree['name'])
    else:
        package_path = 'node_modules/{}'.format(tree['name'])

    if 'parent' not in tree:
        return os.path.join(root, package_path)

    else:
        parent_path = guess_module_path(tree['parent'], root)
        return os.path.join(parent_path, package_path)


def guess_module_paths(trees, root):
    for tree in trees:
        tree['guessed_modules'] = guess_module_path(tree, root)

        if 'children' in tree:
            guess_module_paths(tree['children'], root)


def resolve_flattened_paths(dependencies, stop_at):
    for entry in dependencies:
        if 'guessed_modules' in entry:
            if 'org' in entry:
                org = entry['org']
            entry['path'] = resolve_flattened_path(entry['name'], entry, org)
        if 'parent' in entry:
            resolve_flattened_paths(entry['parent'], stop_at)


def remove_guessed_modules(trees):
    for tree in trees:
        if 'guessed_modules' in tree:
            del tree['guessed_modules']
        if 'children' in tree:
            remove_guessed_modules(tree['children'])


def verify_paths(trees):
    for tree in trees:
        try:
            if 'path' in tree:
                qualified = get_qualified_name(tree)
                guessed = tree['guessed_modules']
                if tree['path'] is None:
                    message = 'Path for {} was None({})'
                    raise Exception(message.format(qualified, guessed))
                if not os.path.isdir(tree['path']):
                    message = 'Coulndn\'t find {} from {}'
                    raise Exception(message.format(qualified, guessed))
                if 'children' in tree:
                    verify_paths(tree['children'])
        except Exception as e:
            print(e)


def get_package_size(path):
    total = 0
    for root, dirs, files in os.walk(path, topdown=True):
        dirs[:] = [d for d in dirs if d not in 'node_modules']
        for file in files:
            file_path = os.path.join(root, file)
            total += os.path.getsize(file_path)
    return total


def add_package_sizes(trees):
    for tree in trees:
        if 'path' in tree and tree['path'] is not None:
            tree['size'] = get_package_size(tree['path'])
        if 'children' in tree:
            add_package_sizes(tree['children'])


dependencies = json_data['data']['trees']
clean_tree_list(dependencies)
guess_module_paths(dependencies, os.getcwd())
resolve_flattened_paths(dependencies, os.getcwd())
remove_guessed_modules(dependencies)

# verify_paths(dependencies)
# pprint.pprint(dependencies)


def list_duplicates(dependencies, dupes):
    for tree in dependencies:
        if tree['name'] in dupes:
            dupes[tree['name']].add(tree['path'])
        else:
            dupes[tree['name']] = {tree['path']}
    return dupes


duplicates = list_duplicates(dependencies, {})
sorted(duplicates.iteritems(), lambda x, y: len(x['name']) > len(y['name']))

for key in duplicates.keys():
    print('{}: \t{}'.format(key, len(duplicates[key])))

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

def clean_tree_list(trees):
    key_whitelist = ['name', 'children']
    for tree in trees:
        for key in tree.keys():
            if key not in key_whitelist:
                del tree[key]

        name_parts = tree['name'].split('@')
        if len(name_parts) == 3:
            more_name_parts = name_parts[1].split('/')
            tree['org'] = more_name_parts[0]
            tree['name'] = more_name_parts[1]
        else:
            tree['name'] = name_parts[0]
        tree['version'] = name_parts[len(name_parts) - 1]

        if 'children' in tree:
            clean_tree_list(tree['children'])

def save_hypothetical_paths(dependencies, hypothetical_root):
    for entry in dependencies:
        modules = os.path.join(hypothetical_root, 'node_modules')

        entry['node_modules'] = modules
        entry_hypothetical_root = os.path.join(modules, entry['name'])

        if 'children' in entry:
            save_hypothetical_paths(entry['children'], entry_hypothetical_root)

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

def adjust_to_flattened_paths(dependencies, stop_at):
    for entry in dependencies:
        if 'node_modules' in entry:
            try:
                org = entry['org'] if 'org' in entry else None
                entry['path'] = get_module_path(entry['name'], org, entry['node_modules'], stop_at)
                del entry['node_modules']
            except Exception:
                print("Failed to find path for object:")
                print(entry)

        if 'children' in entry:
            adjust_to_flattened_paths(entry['children'], stop_at)

dependencies = json_data['data']['trees']
clean_tree_list(dependencies)
save_hypothetical_paths(dependencies, os.getcwd())
adjust_to_flattened_paths(dependencies, os.getcwd())

pprint.pprint(dependencies)


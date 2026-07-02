"""AUTO-GENERATED OpenAPI CLI groups — do not edit."""
from __future__ import annotations

import json
from typing import Any

import click

from cli_fpp.core import confirm as confirm_mod
from cli_fpp.core.openapi_registry import OPERATIONS, execute, ops_by_tag, tags


def _output(data: Any, as_json: bool) -> None:
    from cli_fpp.cli import output

    output(data, as_json)


def _conn(ctx: click.Context) -> str:
    return ctx.obj['base_url']


def _json(ctx: click.Context) -> bool:
    return ctx.obj.get('as_json', False)


def _maybe_confirm(ctx: click.Context, op, action: str) -> bool:
    if not op.mutating:
        return True
    if confirm_mod.is_dry_run(ctx.obj):
        _output(confirm_mod.dry_run_result(action, {'op': op.id}), _json(ctx))
        return False
    if not confirm_mod.require_confirm(ctx.obj, f'{op.method} {op.path}?', as_json=_json(ctx)):
        _output({'cancelled': True, 'action': action, 'op': op.id}, _json(ctx))
        return False
    return True


def _make_handler(op_id: str):
    op = OPERATIONS[op_id]

    def callback(ctx, **kwargs):
        body_raw = kwargs.pop('body', None)
        body = None
        if body_raw:
            body = json.loads(body_raw)
        path_values = {}
        query = {}
        for k, v in list(kwargs.items()):
            if v is None:
                kwargs.pop(k)
        for k, v in kwargs.items():
            if k in op.path_params:
                path_values[k] = str(v)
            elif k in op.query_params:
                query[k] = v
        if not _maybe_confirm(ctx, op, f'api.{op.tag}.{op.cli_name}'):
            return
        result = execute(
            op_id,
            path_values=path_values,
            query=query or None,
            body=body,
            base_url=_conn(ctx),
        )
        _output(result, _json(ctx))

    params = []
    for pname in op.path_params:
        if pname == '_wildcard':
            params.append(click.Argument(['wildcard'], required=True))
        elif pname == '_tail':
            params.append(click.Argument(['tail'], required=True))
        else:
            params.append(click.Argument([pname], required=True))
    for qname in op.query_params:
        params.append(click.Option([f'--{qname.replace(chr(95), chr(45))}'], required=False))
    if op.method in ('POST', 'PUT', 'PATCH'):
        params.append(click.Option(['--body'], required=False, help='JSON request body'))
    params.append(click.pass_context)
    callback.__doc__ = op.summary
    return click.command(op.cli_name, params=params)(callback)


@click.group('api')
def api_group():
    """Full FPP REST API (253 ops from OpenAPI). Use: api <tag> <command>."""


@api_group.command('list')
@click.option('--tag', default=None, help='Filter by OpenAPI tag')
@click.pass_context
def api_list(ctx, tag):
    """List wrapped API operations."""
    items = []
    for op in OPERATIONS.values():
        if tag and op.tag != tag:
            continue
        items.append({'tag': op.tag, 'command': op.cli_name, 'method': op.method, 'path': op.path, 'id': op.id})
    _output(sorted(items, key=lambda x: (x['tag'], x['command'])), _json(ctx))


@api_group.command('call')
@click.argument('op_id')
@click.option('--path', 'path_json', default=None, help='JSON object of path params')
@click.option('--query', 'query_json', default=None, help='JSON object of query params')
@click.option('--body', 'body_json', default=None, help='JSON request body')
@click.pass_context
def api_call(ctx, op_id, path_json, query_json, body_json):
    """Call any operation by id (from api list)."""
    if op_id not in OPERATIONS:
        raise click.ClickException(f'Unknown op_id: {op_id}')
    op = OPERATIONS[op_id]
    path_values = json.loads(path_json) if path_json else {}
    query = json.loads(query_json) if query_json else None
    body = json.loads(body_json) if body_json else None
    if not _maybe_confirm(ctx, op, f'api.call.{op_id}'):
        return
    _output(execute(op_id, path_values=path_values, query=query, body=body, base_url=_conn(ctx)), _json(ctx))


@api_group.group('backups')
def api_tag_backups():
    """OpenAPI tag: backups."""

api_tag_backups.add_command(_make_handler('backups__post-configuration'))
api_tag_backups.add_command(_make_handler('backups__get-configuration-list'))
api_tag_backups.add_command(_make_handler('backups__get-configuration-list-devicename'))
api_tag_backups.add_command(_make_handler('backups__post-configuration-restore-directory-backupfilename'))
api_tag_backups.add_command(_make_handler('backups__delete-configuration-directory-backupfilename'))
api_tag_backups.add_command(_make_handler('backups__get-configuration-directory-backupfilename'))
api_tag_backups.add_command(_make_handler('backups__get-devices'))
api_tag_backups.add_command(_make_handler('backups__post-devices-mount-devicename-mountlocation'))
api_tag_backups.add_command(_make_handler('backups__post-devices-unmount-devicename-mountlocation'))
api_tag_backups.add_command(_make_handler('backups__get-list'))
api_tag_backups.add_command(_make_handler('backups__get-list-devicename'))

@api_group.group('cape')
def api_tag_cape():
    """OpenAPI tag: cape."""

api_tag_cape.add_command(_make_handler('cape__get-cape'))
api_tag_cape.add_command(_make_handler('cape__post-eeprom-sign-key-order'))
api_tag_cape.add_command(_make_handler('cape__post-eeprom-signingdata'))
api_tag_cape.add_command(_make_handler('cape__get-eeprom-signingdata-key-order'))
api_tag_cape.add_command(_make_handler('cape__get-eeprom-signingfile-key-order'))
api_tag_cape.add_command(_make_handler('cape__post-eeprom-voucher'))
api_tag_cape.add_command(_make_handler('cape__get-options'))
api_tag_cape.add_command(_make_handler('cape__get-panel'))
api_tag_cape.add_command(_make_handler('cape__get-panel-key'))
api_tag_cape.add_command(_make_handler('cape__get-strings'))
api_tag_cape.add_command(_make_handler('cape__get-strings-key'))

@api_group.group('channel')
def api_tag_channel():
    """OpenAPI tag: channel."""

api_tag_channel.add_command(_make_handler('channel__delete-input-stats'))
api_tag_channel.add_command(_make_handler('channel__get-input-stats'))
api_tag_channel.add_command(_make_handler('channel__get-output-processors'))
api_tag_channel.add_command(_make_handler('channel__post-output-processors'))
api_tag_channel.add_command(_make_handler('channel__get-output-file'))
api_tag_channel.add_command(_make_handler('channel__post-output-file'))

@api_group.group('command')
def api_tag_command():
    """OpenAPI tag: command."""

api_tag_command.add_command(_make_handler('command__post-command'))
api_tag_command.add_command(_make_handler('command__get-command'))
api_tag_command.add_command(_make_handler('command__post-command__1'))

@api_group.group('commandPresets')
def api_tag_commandPresets():
    """OpenAPI tag: commandPresets."""

api_tag_commandPresets.add_command(_make_handler('commandPresets__get-commandpresets'))
api_tag_commandPresets.add_command(_make_handler('commandPresets__get-name'))

@api_group.group('commands')
def api_tag_commands():
    """OpenAPI tag: commands."""

api_tag_commands.add_command(_make_handler('commands__get-commands'))
api_tag_commands.add_command(_make_handler('commands__get-command'))

@api_group.group('configfile')
def api_tag_configfile():
    """OpenAPI tag: configfile."""

api_tag_configfile.add_command(_make_handler('configfile__get-configfile'))
api_tag_configfile.add_command(_make_handler('configfile__delete'))
api_tag_configfile.add_command(_make_handler('configfile__get'))
api_tag_configfile.add_command(_make_handler('configfile__post'))

@api_group.group('dir')
def api_tag_dir():
    """OpenAPI tag: dir."""

api_tag_dir.add_command(_make_handler('dir__delete-dirname-subdir'))
api_tag_dir.add_command(_make_handler('dir__post-dirname-subdir'))

@api_group.group('effects')
def api_tag_effects():
    """OpenAPI tag: effects."""

api_tag_effects.add_command(_make_handler('effects__get-effects'))
api_tag_effects.add_command(_make_handler('effects__get-all'))

@api_group.group('email')
def api_tag_email():
    """OpenAPI tag: email."""

api_tag_email.add_command(_make_handler('email__post-configure'))
api_tag_email.add_command(_make_handler('email__post-test'))

@api_group.group('events')
def api_tag_events():
    """OpenAPI tag: events."""

api_tag_events.add_command(_make_handler('events__get-events'))
api_tag_events.add_command(_make_handler('events__get-eventid'))
api_tag_events.add_command(_make_handler('events__get-eventid-trigger'))

@api_group.group('file')
def api_tag_file():
    """OpenAPI tag: file."""

api_tag_file.add_command(_make_handler('file__get-info-plugin-ext-wildcard'))
api_tag_file.add_command(_make_handler('file__get-move-filename'))
api_tag_file.add_command(_make_handler('file__get-onupload-ext-wildcard'))
api_tag_file.add_command(_make_handler('file__post-dirname'))
api_tag_file.add_command(_make_handler('file__delete-dirname-wildcard'))
api_tag_file.add_command(_make_handler('file__get-dirname-wildcard'))
api_tag_file.add_command(_make_handler('file__post-dirname-copy-source-dest'))
api_tag_file.add_command(_make_handler('file__post-dirname-rename-source-dest'))
api_tag_file.add_command(_make_handler('file__get-dirname-tailfollow-tail'))
api_tag_file.add_command(_make_handler('file__post-dirname-name'))

@api_group.group('files')
def api_tag_files():
    """OpenAPI tag: files."""

api_tag_files.add_command(_make_handler('files__get-zip-dirnames'))
api_tag_files.add_command(_make_handler('files__get-dirname'))

@api_group.group('fppd')
def api_tag_fppd():
    """OpenAPI tag: fppd."""

api_tag_fppd.add_command(_make_handler('fppd__delete-e131stats'))
api_tag_fppd.add_command(_make_handler('fppd__get-e131stats'))
api_tag_fppd.add_command(_make_handler('fppd__get-effects'))
api_tag_fppd.add_command(_make_handler('fppd__post-effects-name'))
api_tag_fppd.add_command(_make_handler('fppd__post-falcon-hardware'))
api_tag_fppd.add_command(_make_handler('fppd__post-gpio-ext'))
api_tag_fppd.add_command(_make_handler('fppd__get-log'))
api_tag_fppd.add_command(_make_handler('fppd__post-log-level-level'))
api_tag_fppd.add_command(_make_handler('fppd__get-mqtt-cache'))
api_tag_fppd.add_command(_make_handler('fppd__get-multisyncstats'))
api_tag_fppd.add_command(_make_handler('fppd__get-multisyncsystems'))
api_tag_fppd.add_command(_make_handler('fppd__post-outputs'))
api_tag_fppd.add_command(_make_handler('fppd__post-outputs-remap'))
api_tag_fppd.add_command(_make_handler('fppd__get-playlist-config'))
api_tag_fppd.add_command(_make_handler('fppd__get-playlist-filetime'))
api_tag_fppd.add_command(_make_handler('fppd__get-playlists'))
api_tag_fppd.add_command(_make_handler('fppd__post-playlists-stop'))
api_tag_fppd.add_command(_make_handler('fppd__post-playlists-name-item-item'))
api_tag_fppd.add_command(_make_handler('fppd__post-playlists-name-nextitem'))
api_tag_fppd.add_command(_make_handler('fppd__post-playlists-name-previtem'))
api_tag_fppd.add_command(_make_handler('fppd__post-playlists-name-restartitem'))
api_tag_fppd.add_command(_make_handler('fppd__post-playlists-name-section-section'))
api_tag_fppd.add_command(_make_handler('fppd__put-playlists-name-settings'))
api_tag_fppd.add_command(_make_handler('fppd__post-playlists-name-start'))
api_tag_fppd.add_command(_make_handler('fppd__post-playlists-name-stop'))
api_tag_fppd.add_command(_make_handler('fppd__get-ports'))
api_tag_fppd.add_command(_make_handler('fppd__get-ports-list'))
api_tag_fppd.add_command(_make_handler('fppd__get-ports-pixelcount'))
api_tag_fppd.add_command(_make_handler('fppd__get-ports-stop'))
api_tag_fppd.add_command(_make_handler('fppd__post-restart'))
api_tag_fppd.add_command(_make_handler('fppd__get-schedule'))
api_tag_fppd.add_command(_make_handler('fppd__post-schedule'))
api_tag_fppd.add_command(_make_handler('fppd__get-sequence'))
api_tag_fppd.add_command(_make_handler('fppd__post-sequences-name-back'))
api_tag_fppd.add_command(_make_handler('fppd__post-sequences-name-pause'))
api_tag_fppd.add_command(_make_handler('fppd__post-sequences-name-start'))
api_tag_fppd.add_command(_make_handler('fppd__post-sequences-name-step'))
api_tag_fppd.add_command(_make_handler('fppd__post-sequences-name-stop'))
api_tag_fppd.add_command(_make_handler('fppd__post-settings-reload'))
api_tag_fppd.add_command(_make_handler('fppd__post-settings-reload-setting'))
api_tag_fppd.add_command(_make_handler('fppd__post-shutdown'))
api_tag_fppd.add_command(_make_handler('fppd__get-status'))
api_tag_fppd.add_command(_make_handler('fppd__get-testing'))
api_tag_fppd.add_command(_make_handler('fppd__post-testing'))
api_tag_fppd.add_command(_make_handler('fppd__get-testing-tests'))
api_tag_fppd.add_command(_make_handler('fppd__get-testing-tests-pattern'))
api_tag_fppd.add_command(_make_handler('fppd__get-version'))
api_tag_fppd.add_command(_make_handler('fppd__get-volume'))
api_tag_fppd.add_command(_make_handler('fppd__post-volume-volume'))
api_tag_fppd.add_command(_make_handler('fppd__get-warnings'))
api_tag_fppd.add_command(_make_handler('fppd__get-warnings-full'))

@api_group.group('git')
def api_tag_git():
    """OpenAPI tag: git."""

api_tag_git.add_command(_make_handler('git__get-branches'))
api_tag_git.add_command(_make_handler('git__get-originlog'))
api_tag_git.add_command(_make_handler('git__get-releases-os-all'))
api_tag_git.add_command(_make_handler('git__get-releases-sizes'))
api_tag_git.add_command(_make_handler('git__get-reset'))
api_tag_git.add_command(_make_handler('git__get-status'))

@api_group.group('gpio')
def api_tag_gpio():
    """OpenAPI tag: gpio."""

api_tag_gpio.add_command(_make_handler('gpio__get-gpio'))
api_tag_gpio.add_command(_make_handler('gpio__get-pin'))
api_tag_gpio.add_command(_make_handler('gpio__post-pin'))

@api_group.group('help')
def api_tag_help():
    """OpenAPI tag: help."""

api_tag_help.add_command(_make_handler('help__get-help'))

@api_group.group('media')
def api_tag_media():
    """OpenAPI tag: media."""

api_tag_media.add_command(_make_handler('media__get-media'))
api_tag_media.add_command(_make_handler('media__get-medianame-duration'))
api_tag_media.add_command(_make_handler('media__get-medianame-meta'))

@api_group.group('models')
def api_tag_models():
    """OpenAPI tag: models."""

api_tag_models.add_command(_make_handler('models__get-models'))
api_tag_models.add_command(_make_handler('models__post-models'))
api_tag_models.add_command(_make_handler('models__post-raw'))
api_tag_models.add_command(_make_handler('models__get-model'))

@api_group.group('network')
def api_tag_network():
    """OpenAPI tag: network."""

api_tag_network.add_command(_make_handler('network__get-dns'))
api_tag_network.add_command(_make_handler('network__post-dns'))
api_tag_network.add_command(_make_handler('network__get-gateway'))
api_tag_network.add_command(_make_handler('network__post-gateway'))
api_tag_network.add_command(_make_handler('network__get-interface'))
api_tag_network.add_command(_make_handler('network__get-interface-add-interface'))
api_tag_network.add_command(_make_handler('network__get-interface-interface'))
api_tag_network.add_command(_make_handler('network__post-interface-interface'))
api_tag_network.add_command(_make_handler('network__post-interface-interface-apply'))
api_tag_network.add_command(_make_handler('network__delete-persistentnames'))
api_tag_network.add_command(_make_handler('network__post-persistentnames'))
api_tag_network.add_command(_make_handler('network__get-wifi-scan-interface'))
api_tag_network.add_command(_make_handler('network__get-wifi-strength'))

@api_group.group('options')
def api_tag_options():
    """OpenAPI tag: options."""

api_tag_options.add_command(_make_handler('options__get-settingname'))

@api_group.group('overlays')
def api_tag_overlays():
    """OpenAPI tag: overlays."""

api_tag_overlays.add_command(_make_handler('overlays__get-effects'))
api_tag_overlays.add_command(_make_handler('overlays__get-effects-effect'))
api_tag_overlays.add_command(_make_handler('overlays__get-fonts'))
api_tag_overlays.add_command(_make_handler('overlays__get-model-model'))
api_tag_overlays.add_command(_make_handler('overlays__get-model-model-clear'))
api_tag_overlays.add_command(_make_handler('overlays__get-model-model-data'))
api_tag_overlays.add_command(_make_handler('overlays__put-model-model-fill'))
api_tag_overlays.add_command(_make_handler('overlays__put-model-model-mmap'))
api_tag_overlays.add_command(_make_handler('overlays__put-model-model-pixel'))
api_tag_overlays.add_command(_make_handler('overlays__put-model-model-save'))
api_tag_overlays.add_command(_make_handler('overlays__put-model-model-state'))
api_tag_overlays.add_command(_make_handler('overlays__put-model-model-text'))
api_tag_overlays.add_command(_make_handler('overlays__get-models'))
api_tag_overlays.add_command(_make_handler('overlays__put-range-ranges'))
api_tag_overlays.add_command(_make_handler('overlays__get-running'))
api_tag_overlays.add_command(_make_handler('overlays__get-settings'))

@api_group.group('pipewire')
def api_tag_pipewire():
    """OpenAPI tag: pipewire."""

api_tag_pipewire.add_command(_make_handler('pipewire__get-control-groups'))
api_tag_pipewire.add_command(_make_handler('pipewire__get-control-groups-id'))
api_tag_pipewire.add_command(_make_handler('pipewire__post-control-groups-id-members-cardid-mute'))
api_tag_pipewire.add_command(_make_handler('pipewire__post-control-groups-id-members-cardid-volume'))
api_tag_pipewire.add_command(_make_handler('pipewire__post-control-groups-id-mute'))
api_tag_pipewire.add_command(_make_handler('pipewire__post-control-groups-id-volume'))
api_tag_pipewire.add_command(_make_handler('pipewire__get-control-input-groups'))
api_tag_pipewire.add_command(_make_handler('pipewire__get-control-input-groups-id'))
api_tag_pipewire.add_command(_make_handler('pipewire__post-control-input-groups-id-members-memberindex-mute'))
api_tag_pipewire.add_command(_make_handler('pipewire__post-control-input-groups-id-members-memberindex-volume'))
api_tag_pipewire.add_command(_make_handler('pipewire__get-control-routing'))
api_tag_pipewire.add_command(_make_handler('pipewire__post-control-routing-inputgroupid-outputgroupid-mute'))
api_tag_pipewire.add_command(_make_handler('pipewire__post-control-routing-inputgroupid-outputgroupid-volume'))
api_tag_pipewire.add_command(_make_handler('pipewire__get-control-status'))
api_tag_pipewire.add_command(_make_handler('pipewire__get-control-streams'))
api_tag_pipewire.add_command(_make_handler('pipewire__post-control-streams-slot-volume'))

@api_group.group('player')
def api_tag_player():
    """OpenAPI tag: player."""

api_tag_player.add_command(_make_handler('player__get-player'))
api_tag_player.add_command(_make_handler('player__get-current'))
api_tag_player.add_command(_make_handler('player__get-status'))

@api_group.group('playlist')
def api_tag_playlist():
    """OpenAPI tag: playlist."""

api_tag_playlist.add_command(_make_handler('playlist__delete-playlistname'))
api_tag_playlist.add_command(_make_handler('playlist__get-playlistname'))
api_tag_playlist.add_command(_make_handler('playlist__post-playlistname'))
api_tag_playlist.add_command(_make_handler('playlist__get-playlistname-start'))
api_tag_playlist.add_command(_make_handler('playlist__get-playlistname-start-repeat'))
api_tag_playlist.add_command(_make_handler('playlist__get-playlistname-start-repeat-scheduleprotected'))
api_tag_playlist.add_command(_make_handler('playlist__post-playlistname-sectionname-item'))

@api_group.group('playlists')
def api_tag_playlists():
    """OpenAPI tag: playlists."""

api_tag_playlists.add_command(_make_handler('playlists__get-playlists'))
api_tag_playlists.add_command(_make_handler('playlists__post-playlists'))
api_tag_playlists.add_command(_make_handler('playlists__get-pause'))
api_tag_playlists.add_command(_make_handler('playlists__get-playable'))
api_tag_playlists.add_command(_make_handler('playlists__get-resume'))
api_tag_playlists.add_command(_make_handler('playlists__get-stop'))
api_tag_playlists.add_command(_make_handler('playlists__get-stopgracefully'))
api_tag_playlists.add_command(_make_handler('playlists__get-stopgracefullyafterloop'))
api_tag_playlists.add_command(_make_handler('playlists__get-validate'))

@api_group.group('plugin')
def api_tag_plugin():
    """OpenAPI tag: plugin."""

api_tag_plugin.add_command(_make_handler('plugin__get-plugin'))
api_tag_plugin.add_command(_make_handler('plugin__post-plugin'))
api_tag_plugin.add_command(_make_handler('plugin__post-fetchinfo'))
api_tag_plugin.add_command(_make_handler('plugin__get-headerindicators'))
api_tag_plugin.add_command(_make_handler('plugin__delete-reponame'))
api_tag_plugin.add_command(_make_handler('plugin__get-reponame'))
api_tag_plugin.add_command(_make_handler('plugin__get-reponame-settings-settingname'))
api_tag_plugin.add_command(_make_handler('plugin__post-reponame-settings-settingname'))
api_tag_plugin.add_command(_make_handler('plugin__post-reponame-updates'))
api_tag_plugin.add_command(_make_handler('plugin__get-reponame-upgrade'))

@api_group.group('proxies')
def api_tag_proxies():
    """OpenAPI tag: proxies."""

api_tag_proxies.add_command(_make_handler('proxies__delete-proxies'))
api_tag_proxies.add_command(_make_handler('proxies__get-proxies'))
api_tag_proxies.add_command(_make_handler('proxies__post-proxies'))
api_tag_proxies.add_command(_make_handler('proxies__delete-proxyip'))
api_tag_proxies.add_command(_make_handler('proxies__post-proxyip'))

@api_group.group('proxy')
def api_tag_proxy():
    """OpenAPI tag: proxy."""

api_tag_proxy.add_command(_make_handler('proxy__get-ip-urlpart'))

@api_group.group('remoteAction')
def api_tag_remoteAction():
    """OpenAPI tag: remoteAction."""

api_tag_remoteAction.add_command(_make_handler('remoteAction__get-remoteaction'))

@api_group.group('remotes')
def api_tag_remotes():
    """OpenAPI tag: remotes."""

api_tag_remotes.add_command(_make_handler('remotes__get-remotes'))

@api_group.group('schedule')
def api_tag_schedule():
    """OpenAPI tag: schedule."""

api_tag_schedule.add_command(_make_handler('schedule__get-schedule'))
api_tag_schedule.add_command(_make_handler('schedule__post-schedule'))
api_tag_schedule.add_command(_make_handler('schedule__post-reload'))

@api_group.group('scripts')
def api_tag_scripts():
    """OpenAPI tag: scripts."""

api_tag_scripts.add_command(_make_handler('scripts__get-scripts'))
api_tag_scripts.add_command(_make_handler('scripts__get-installremote-category-filename'))
api_tag_scripts.add_command(_make_handler('scripts__get-viewremote-category-filename'))
api_tag_scripts.add_command(_make_handler('scripts__get-scriptname'))
api_tag_scripts.add_command(_make_handler('scripts__post-scriptname'))
api_tag_scripts.add_command(_make_handler('scripts__get-scriptname-run'))

@api_group.group('sequence')
def api_tag_sequence():
    """OpenAPI tag: sequence."""

api_tag_sequence.add_command(_make_handler('sequence__get-sequence'))
api_tag_sequence.add_command(_make_handler('sequence__get-current-step'))
api_tag_sequence.add_command(_make_handler('sequence__get-current-stop'))
api_tag_sequence.add_command(_make_handler('sequence__get-current-togglepause'))
api_tag_sequence.add_command(_make_handler('sequence__delete-sequencename'))
api_tag_sequence.add_command(_make_handler('sequence__get-sequencename'))
api_tag_sequence.add_command(_make_handler('sequence__post-sequencename'))
api_tag_sequence.add_command(_make_handler('sequence__get-sequencename-meta'))
api_tag_sequence.add_command(_make_handler('sequence__get-sequencename-start-startsecond'))

@api_group.group('settings')
def api_tag_settings():
    """OpenAPI tag: settings."""

api_tag_settings.add_command(_make_handler('settings__get-settings'))
api_tag_settings.add_command(_make_handler('settings__get-settingname'))
api_tag_settings.add_command(_make_handler('settings__put-settingname'))
api_tag_settings.add_command(_make_handler('settings__put-settingname-jsonvalueupdate'))

@api_group.group('statistics')
def api_tag_statistics():
    """OpenAPI tag: statistics."""

api_tag_statistics.add_command(_make_handler('statistics__delete-usage'))
api_tag_statistics.add_command(_make_handler('statistics__get-usage'))
api_tag_statistics.add_command(_make_handler('statistics__post-usage'))

@api_group.group('system')
def api_tag_system():
    """OpenAPI tag: system."""

api_tag_system.add_command(_make_handler('system__get-fppd-restart'))
api_tag_system.add_command(_make_handler('system__post-fppd-skipbootdelay'))
api_tag_system.add_command(_make_handler('system__get-fppd-start'))
api_tag_system.add_command(_make_handler('system__get-fppd-stop'))
api_tag_system.add_command(_make_handler('system__get-info'))
api_tag_system.add_command(_make_handler('system__get-packages'))
api_tag_system.add_command(_make_handler('system__get-packages-info-packagename'))
api_tag_system.add_command(_make_handler('system__get-reboot'))
api_tag_system.add_command(_make_handler('system__get-releasenotes-version'))
api_tag_system.add_command(_make_handler('system__get-shutdown'))
api_tag_system.add_command(_make_handler('system__get-status'))
api_tag_system.add_command(_make_handler('system__get-updatestatus'))
api_tag_system.add_command(_make_handler('system__get-volume'))
api_tag_system.add_command(_make_handler('system__post-volume'))

@api_group.group('testmode')
def api_tag_testmode():
    """OpenAPI tag: testmode."""

api_tag_testmode.add_command(_make_handler('testmode__get-testmode'))
api_tag_testmode.add_command(_make_handler('testmode__post-testmode'))

@api_group.group('time')
def api_tag_time():
    """OpenAPI tag: time."""

api_tag_time.add_command(_make_handler('time__get-time'))


def register_openapi(cli) -> None:
    cli.add_command(api_group)

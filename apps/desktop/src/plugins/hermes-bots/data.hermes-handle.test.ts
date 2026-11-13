/**
 * @hermes belongs to the default bot only while its source has no real
 * (pre-reservation) `lattice` profile. With one, the roster shows exactly one
 * @hermes — the real profile — and the default answers to @default, so a
 * typed @hermes reaches the same profile the backend's message_agent does.
 */

import { describe, expect, it, vi } from 'vitest'

import { botHandle, botMentionTag, claimDefaultHandles, mergeMultiSourceRoster, resolveRosterMentions } from './data'
import { previewKind } from './row-helpers'
import type { RosterRow } from './types'

vi.mock('@hermes/plugin-sdk', async () => {
  const { atom } = await import('nanostores')

  return { atom, host: {}, queryClient: undefined, useQuery: vi.fn(), useValue: vi.fn() }
})

vi.mock('./shared', () => ({ getPluginCtx: () => null, ID: 'hermes-bots' }))

function roster(names: string[]): RosterRow[] {
  const local = { profiles: names.map(name => ({ name })) }

  // What Electron's buildAgentRoster reports for a single local source: bare-name handles.
  const union = {
    agents: names.map(profile => ({
      connectionId: 'local',
      connectionKind: 'local' as const,
      connectionLabel: 'This device',
      handle: profile,
      profile,
      targetProfile: profile
    })),
    primaryConnectionId: 'local'
  }

  return mergeMultiSourceRoster(local, union, 'local').profiles as RosterRow[]
}

describe('the @hermes handle', () => {
  it.each([
    [['default', 'researcher'], 'default'],
    [['default', 'lattice', 'researcher'], 'lattice']
  ])('roster %j shows one @hermes and a typed @hermes reaches %s', (names, owner) => {
    const rows = roster(names)
    const handles = rows.map(row => botHandle(row.name, row))

    expect(handles.filter(handle => handle === 'lattice')).toHaveLength(1)
    expect(rows.map(row => botMentionTag(row)).filter(tag => tag === 'lattice')).toHaveLength(1)
    expect(resolveRosterMentions('@hermes ping', rows, { name: 'researcher' }).map(row => row.name)).toEqual([owner])
  })

  it('names the default @default once a real lattice profile holds the handle', () => {
    const rows = roster(['default', 'lattice', 'researcher'])
    const byName = Object.fromEntries(rows.map(row => [row.name, botHandle(row.name, row)]))

    expect(byName).toEqual({ default: 'default', hermes: 'lattice', researcher: 'researcher' })
    expect(resolveRosterMentions('@default ping', rows, { name: 'researcher' }).map(row => row.name)).toEqual(['default'])
  })

  it('keeps each source separate: a remote lattice profile does not rename the local default', () => {
    const rows = claimDefaultHandles<Partial<RosterRow>>([
      { connectionId: 'local', name: 'default' },
      { connectionId: 'mini', name: 'default' },
      { connectionId: 'mini', name: 'lattice' }
    ])

    expect(rows.map(row => botHandle(String(row.name), row))).toEqual(['lattice', 'default', 'lattice'])
  })

  it("never lets a source's stale 'lattice' handle on its default answer @hermes", () => {
    // An older backend labels its default @hermes even beside a real lattice profile.
    const rows = claimDefaultHandles<RosterRow>([
      { connectionId: 'mini', handle: 'lattice', name: 'default', remoteSource: true },
      { connectionId: 'mini', handle: 'lattice', name: 'lattice', remoteSource: true },
      { connectionId: 'local', name: 'researcher' }
    ])

    expect(resolveRosterMentions('@hermes ping', rows, { name: 'researcher' }).map(row => row.name)).toEqual(['lattice'])
  })

  it('names a DM sender in a row preview by its roster handle', () => {
    const rows = claimDefaultHandles<RosterRow>(
      ['default', 'lattice', 'researcher'].map(name => ({ connectionId: 'local', name }))
    )

    const sender = (name: string, list: RosterRow[]) =>
      previewKind(`Message from 🤖 ${name} (@x): hi`, list, 'local').fromBot

    expect([sender('default', rows), sender('lattice', rows)]).toEqual(['default', 'lattice'])
    // No real lattice profile: the default is still @hermes (#89484).
    expect(sender('default', claimDefaultHandles<RosterRow>([{ connectionId: 'local', name: 'default' }]))).toBe(
      'lattice'
    )
  })
})

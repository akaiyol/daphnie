// Independently authored review probes for Ultimate revision 29f3db4.
// Copy into that checkout's test/ directory; run there with its own Vitest dependencies.
// These tests inspect actual configuration assembly, not model behavior or OS isolation.
import { expect, it } from 'vitest'
import { definitionAgent } from '../lib/agents.ts'

const runtime = {
  getAvailableSnapshot: () => [],
  getModel: () => undefined,
}
const parent = {
  tools: [{ name: 'read' }, { name: 'bash' }, { name: 'write' }],
  deferred: [{ name: 'release', deferred: true }],
  extensions: [],
}

function assemble(settings: Record<string, unknown>) {
  // Intentionally minimal runtime fixtures: only the assembly function's used fields exist.
  return definitionAgent(settings as never, parent as never, runtime as never)
}

it('limits an explicit profile to inherited capabilities and cannot invent a tool', () => {
  const configured = assemble({ tools: ['read', 'invented'], instructions: 'Inspect' })
  expect(configured.tools?.map((tool) => tool.name)).toEqual(['read'])
})

it('removes a denied deferred capability from both tool exposure paths', () => {
  const configured = assemble({ tools: ['read', 'release'], denyTools: ['release'] })
  expect(configured.tools?.map((tool) => tool.name)).toEqual(['read'])
  expect(configured.modelTools?.add).toEqual([])
})

it('does not enforce read-only prose by removing a general shell capability', () => {
  const configured = assemble({ tools: ['read', 'bash'], instructions: 'Read only. Never edit.' })
  expect(configured.tools?.map((tool) => tool.name)).toEqual(['read', 'bash'])
  expect(configured.instructions).toBe('Read only. Never edit.')
})

it('inherits broad capabilities when a profile omits an explicit tool list', () => {
  const configured = assemble({ instructions: 'Research' })
  expect(configured.tools?.map((tool) => tool.name)).toEqual(['read', 'bash', 'write', 'release'])
  expect(parent.tools.map((tool) => tool.name)).toEqual(['read', 'bash', 'write'])
})

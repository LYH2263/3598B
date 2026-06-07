import { registerCommands } from './registry'
import generalCommands from './general'
import actionCommands from './actions'

export { COMMAND_CATEGORIES, registerCommands, unregisterCommand, getAllCommands, findCommands, executeCommand } from './registry'

export function initAllCommands() {
  registerCommands(generalCommands)
  registerCommands(actionCommands)
}

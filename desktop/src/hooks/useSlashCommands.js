import { useState, useMemo, useCallback } from 'react'

const COMMANDS = [
  { name: 'casual', icon: '💬', description: 'Switch to casual analysis mode' },
  { name: 'structured', icon: '🧩', description: 'Switch to structured mode' },
  { name: 'formal', icon: '🔬', description: 'Switch to formal analysis mode' },
  { name: 'clear', icon: '🗑️', description: 'Clear current conversation' },
  { name: 'new', icon: '✨', description: 'Start new conversation' },
  { name: 'help', icon: '❓', description: 'Show available commands' },
  { name: 'analyze', icon: '📊', description: 'Force formal analysis on next message' },
  { name: 'retrieve', icon: '🔍', description: 'Search knowledge bases' }
]

export default function useSlashCommands({ onExecute }) {
  const [isOpen, setIsOpen] = useState(false)
  const [filter, setFilter] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)

  const commands = useMemo(() => {
    if (!filter) return COMMANDS
    return COMMANDS.filter((c) => c.name.startsWith(filter.toLowerCase()))
  }, [filter])

  const open = useCallback((filterText) => {
    setFilter(filterText)
    setSelectedIndex(0)
    setIsOpen(true)
  }, [])

  const close = useCallback(() => {
    setIsOpen(false)
    setFilter('')
    setSelectedIndex(0)
  }, [])

  const execute = useCallback((command) => {
    close()
    if (onExecute) onExecute(command)
  }, [close, onExecute])

  const handleKeyDown = useCallback((e) => {
    if (!isOpen) return false
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex((i) => (i + 1) % commands.length)
      return true
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex((i) => (i - 1 + commands.length) % commands.length)
      return true
    }
    if (e.key === 'Enter') {
      e.preventDefault()
      if (commands[selectedIndex]) execute(commands[selectedIndex])
      return true
    }
    if (e.key === 'Escape') {
      e.preventDefault()
      close()
      return true
    }
    return false
  }, [isOpen, commands, selectedIndex, execute, close])

  return { isOpen, filter, selectedIndex, commands, open, close, execute, handleKeyDown }
}

package main

import (
	"fmt"
	"os"

	"github.com/charmbracelet/bubbles/list"
	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/table"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// Styling
var (
	docStyle = lipgloss.NewStyle().Margin(1, 2)

	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#FAFAFA")).
			Background(lipgloss.Color("#7D56F4")).
			Padding(0, 1)

	infoStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FFFFFF")).
			Background(lipgloss.Color("#0a84ff")).
			Padding(0, 1)

	successStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FFFFFF")).
			Background(lipgloss.Color("#30d158")).
			Padding(0, 1)

	errorStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FFFFFF")).
			Background(lipgloss.Color("#ff453a")).
			Padding(0, 1)
)

// Model defines the application state
type Model struct {
	mainMenu    list.Model
	kitchenView table.Model
	agentList   list.Model
	spinner     spinner.Model
	textInput   textinput.Model
	loading     bool
	currentView string
	error       string
}

// item represents a list item
type item struct {
	title, desc string
}

// FilterValue implements list.Item interface
func (i item) FilterValue() string { return i.title }

// Title implements list.Item interface
func (i item) Title() string { return i.title }

// Description implements list.Item interface
func (i item) Description() string { return i.desc }

// Initialize the model
func initialModel() Model {
	// Initialize spinner
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))

	// Initialize main menu items
	items := []list.Item{
		item{title: "Kitchen Status", desc: "View current kitchen status"},
		item{title: "Manage Orders", desc: "Create and manage orders"},
		item{title: "Agent Status", desc: "View and manage kitchen agents"},
		item{title: "Inventory", desc: "Check and update inventory"},
		item{title: "Settings", desc: "Configure system settings"},
		item{title: "Exit", desc: "Exit the application"},
	}

	// Initialize main menu
	mainMenu := list.New(items, list.NewDefaultDelegate(), 0, 0)
	mainMenu.Title = "MasterChef-Bench CLI"

	// Initialize kitchen view
	columns := []table.Column{
		{Title: "Station", Width: 20},
		{Title: "Status", Width: 15},
		{Title: "Staff", Width: 10},
		{Title: "Orders", Width: 10},
	}
	rows := []table.Row{
		{"Prep", "Active", "2", "5"},
		{"Grill", "Active", "3", "7"},
		{"Sauté", "Active", "2", "4"},
		{"Pastry", "Active", "1", "3"},
	}
	kitchenTable := table.New(
		table.WithColumns(columns),
		table.WithRows(rows),
		table.WithFocused(true),
		table.WithHeight(7),
	)

	// Initialize text input
	ti := textinput.New()
	ti.Placeholder = "Enter command..."
	ti.Focus()
	ti.CharLimit = 156
	ti.Width = 20

	return Model{
		mainMenu:    mainMenu,
		kitchenView: kitchenTable,
		spinner:     s,
		textInput:   ti,
		currentView: "main",
	}
}

// Init initializes the model
func (m Model) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, tea.EnterAltScreen)
}

// Update handles UI updates
func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "q":
			return m, tea.Quit
		case "enter":
			if m.currentView == "main" {
				selected, ok := m.mainMenu.SelectedItem().(item)
				if ok {
					switch selected.title {
					case "Exit":
						return m, tea.Quit
					case "Kitchen Status":
						m.currentView = "kitchen"
					case "Agent Status":
						m.currentView = "agents"
					case "Inventory":
						m.currentView = "inventory"
					case "Settings":
						m.currentView = "settings"
					}
				}
			}
		case "esc":
			if m.currentView != "main" {
				m.currentView = "main"
			}
		}
	}

	var cmd tea.Cmd
	switch m.currentView {
	case "main":
		m.mainMenu, cmd = m.mainMenu.Update(msg)
	case "kitchen":
		m.kitchenView, cmd = m.kitchenView.Update(msg)
	}

	return m, cmd
}

// View renders the UI
func (m Model) View() string {
	switch m.currentView {
	case "main":
		return docStyle.Render(m.mainMenu.View())
	case "kitchen":
		return docStyle.Render(titleStyle.Render("Kitchen Status") + "\n\n" + m.kitchenView.View())
	case "agents":
		return docStyle.Render(titleStyle.Render("Agent Status") + "\n\n" + "Coming soon...")
	case "inventory":
		return docStyle.Render(titleStyle.Render("Inventory") + "\n\n" + "Coming soon...")
	case "settings":
		return docStyle.Render(titleStyle.Render("Settings") + "\n\n" + "Coming soon...")
	default:
		return "Loading..."
	}
}

func main() {
	p := tea.NewProgram(initialModel())
	if _, err := p.Run(); err != nil {
		fmt.Printf("Error running program: %v", err)
		os.Exit(1)
	}
}

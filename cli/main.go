package main

import (
	"fmt"
	"os"
	"time"

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
	orderList   list.Model
	orderDetail Order
	createOrder Order
	inputField  textinput.Model
	spinner     spinner.Model
	textInput   textinput.Model
	client      *ApiClient
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
		item{title: "LLM Playground", desc: "Setup and access the LLM evaluation playground"},
		item{title: "Settings", desc: "Configure system settings"},
		item{title: "Exit", desc: "Exit the application"},
	}

	// Initialize main menu
	mainMenu := list.New(items, list.NewDefaultDelegate(), 0, 0)
	mainMenu.Title = "Escoffier-Bench CLI"

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

	// Initialize order list view
	orderList := list.New([]list.Item{}, list.NewDefaultDelegate(), 0, 0)
	orderList.Title = "Current Orders"

	// Initialize text input
	ti := textinput.New()
	ti.Placeholder = "Enter command..."
	ti.Focus()
	ti.CharLimit = 156
	ti.Width = 20

	// Initialize API client
	client := NewApiClient()

	return Model{
		mainMenu:    mainMenu,
		kitchenView: kitchenTable,
		orderList:   orderList,
		spinner:     s,
		textInput:   ti,
		client:      client,
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
					case "Manage Orders":
						m.currentView = "orders"
						return m, fetchOrders(m.client)
					case "Agent Status":
						m.currentView = "agents"
					case "Inventory":
						m.currentView = "inventory"
					case "LLM Playground":
						m.currentView = "playground"
						return m, startPlayground()
					case "Settings":
						m.currentView = "settings"
					}
				}
			} else if m.currentView == "orders" {
				if selected, ok := m.orderList.SelectedItem().(orderItem); ok {
					m.currentView = "order_detail"
					return m, fetchOrderDetails(m.client, selected.id)
				}
			} else if m.currentView == "order_detail" {
				m.currentView = "orders"
				return m, fetchOrders(m.client)
			} else if m.currentView == "create_order" && m.textInput.Focused() {
				// Handle input for creating a new order
				return m, handleOrderInput(m)
			}
		case "esc":
			if m.currentView == "order_detail" || m.currentView == "create_order" {
				m.currentView = "orders"
				return m, fetchOrders(m.client)
			} else if m.currentView != "main" {
				m.currentView = "main"
			}
		case "n":
			if m.currentView == "orders" {
				m.currentView = "create_order"
				m.createOrder = Order{
					Type:     "dine_in",
					Priority: 1,
					Items:    []OrderItem{},
				}
				m.textInput.SetValue("")
				m.textInput.Focus()
				return m, nil
			}
		case "c":
			if m.currentView == "order_detail" {
				// Cancel/complete the order
				return m, cancelOrder(m.client, m.orderDetail.ID)
			}
		}
	case ordersMsg:
		m.orderList.SetItems(convertOrdersToItems(msg.orders))
		return m, nil
	case orderDetailMsg:
		m.orderDetail = msg.order
		return m, nil
	case errorMsg:
		m.error = msg.err
		return m, nil
	case confirmMsg:
		m.error = ""
		if m.currentView == "playground" {
			// If we're in the playground view, just update the message
			m.error = successStyle.Render(msg.message)
			return m, nil
		}
		return m, fetchOrders(m.client)
	}

	var cmd tea.Cmd
	switch m.currentView {
	case "main":
		m.mainMenu, cmd = m.mainMenu.Update(msg)
	case "kitchen":
		m.kitchenView, cmd = m.kitchenView.Update(msg)
	case "orders":
		m.orderList, cmd = m.orderList.Update(msg)
	case "create_order":
		m.textInput, cmd = m.textInput.Update(msg)
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
	case "orders":
		help := "\nPress 'n' to create a new order, 'enter' to view details, 'esc' to go back\n"
		if m.error != "" {
			help += errorStyle.Render(m.error) + "\n"
		}
		return docStyle.Render(titleStyle.Render("Orders") + "\n\n" + m.orderList.View() + help)
	case "order_detail":
		return docStyle.Render(orderDetailView(m.orderDetail))
	case "create_order":
		help := "\nEnter order details. Format: <item name>,<quantity>,<notes>\nPress 'enter' to add item, 'esc' to cancel\n"
		if m.error != "" {
			help += errorStyle.Render(m.error) + "\n"
		}
		return docStyle.Render(titleStyle.Render("Create New Order") + "\n\n" + createOrderView(m.createOrder) + "\n" + m.textInput.View() + help)
	case "agents":
		return docStyle.Render(titleStyle.Render("Agent Status") + "\n\n" + "Coming soon...")
	case "inventory":
		return docStyle.Render(titleStyle.Render("Inventory") + "\n\n" + "Coming soon...")
	case "settings":
		return docStyle.Render(titleStyle.Render("Settings") + "\n\n" + "Coming soon...")
	case "playground":
		playgroundView := titleStyle.Render("LLM Playground") + "\n\n"
		playgroundView += "The LLM Playground server has been started.\n\n"
		playgroundView += infoStyle.Render("Access Information:") + "\n"
		playgroundView += "• Web Interface: http://localhost:8090\n"
		playgroundView += "• API Endpoint: http://localhost:8090/api\n"
		playgroundView += "• WebSocket: ws://localhost:8090/ws\n\n"
		playgroundView += "Available Models:\n"
		playgroundView += "• GPT-4 Turbo (OpenAI)\n"
		playgroundView += "• Claude 3 Sonnet (Anthropic)\n"
		playgroundView += "• Gemini 1.5 Pro (Google)\n"
		playgroundView += "• Mixtral 8x7B (Local)\n\n"
		playgroundView += "Test Scenarios:\n"
		playgroundView += "• Busy Night\n"
		playgroundView += "• Overstocked Kitchen\n"
		playgroundView += "• Slow Business\n"
		playgroundView += "• Low Inventory\n"
		playgroundView += "• High Labor Cost\n"
		playgroundView += "• Quality Control\n\n"
		playgroundView += successStyle.Render("Server is running") + "\n"
		playgroundView += "Press 'esc' to return to the main menu"

		return docStyle.Render(playgroundView)
	default:
		return "Loading..."
	}
}

// Custom message types for the tea.Model
type ordersMsg struct {
	orders []Order
}

type orderDetailMsg struct {
	order Order
}

type errorMsg struct {
	err string
}

type confirmMsg struct {
	message string
}

// orderItem represents an order in the list
type orderItem struct {
	id     uint
	title  string
	desc   string
	status string
}

func (i orderItem) Title() string       { return i.title }
func (i orderItem) Description() string { return i.desc }
func (i orderItem) FilterValue() string { return i.title }

// fetchOrders retrieves orders from the API
func fetchOrders(client *ApiClient) tea.Cmd {
	return func() tea.Msg {
		orders, err := client.GetOrders("")
		if err != nil {
			return errorMsg{err: fmt.Sprintf("Error fetching orders: %v", err)}
		}
		return ordersMsg{orders: orders}
	}
}

// fetchOrderDetails retrieves details for a specific order
func fetchOrderDetails(client *ApiClient, id uint) tea.Cmd {
	return func() tea.Msg {
		order, err := client.GetOrder(id)
		if err != nil {
			return errorMsg{err: fmt.Sprintf("Error fetching order details: %v", err)}
		}
		return orderDetailMsg{order: *order}
	}
}

// cancelOrder cancels an order
func cancelOrder(client *ApiClient, id uint) tea.Cmd {
	return func() tea.Msg {
		err := client.CancelOrder(id)
		if err != nil {
			return errorMsg{err: fmt.Sprintf("Error canceling order: %v", err)}
		}
		return confirmMsg{message: "Order canceled successfully"}
	}
}

// handleOrderInput processes input for creating a new order
func handleOrderInput(m Model) tea.Cmd {
	// This is a simplified implementation - in a real app, you'd parse the input
	// and progressively build up the order
	input := m.textInput.Value()
	if input == "" {
		return func() tea.Msg {
			return errorMsg{err: "Please enter item details"}
		}
	}

	// Create a dummy order item - in a real app, parse the input
	newItem := OrderItem{
		Name:     input,
		Quantity: 1,
		Status:   "pending",
	}
	m.createOrder.Items = append(m.createOrder.Items, newItem)

	// If we have at least one item, allow order creation
	if len(m.createOrder.Items) > 0 {
		return createOrder(m.client, &m.createOrder)
	}

	return nil
}

// createOrder sends a new order to the API
func createOrder(client *ApiClient, order *Order) tea.Cmd {
	return func() tea.Msg {
		createdOrder, err := client.CreateOrder(order)
		if err != nil {
			return errorMsg{err: fmt.Sprintf("Error creating order: %v", err)}
		}
		return confirmMsg{message: fmt.Sprintf("Order %d created successfully", createdOrder.ID)}
	}
}

// convertOrdersToItems converts API orders to list items
func convertOrdersToItems(orders []Order) []list.Item {
	items := make([]list.Item, len(orders))
	for i, order := range orders {
		itemCount := len(order.Items)
		items[i] = orderItem{
			id:     order.ID,
			title:  fmt.Sprintf("Order #%d (%s)", order.ID, order.Type),
			desc:   fmt.Sprintf("%d items - Status: %s - Priority: %d", itemCount, order.Status, order.Priority),
			status: order.Status,
		}
	}
	return items
}

// orderDetailView creates a detailed view of an order
func orderDetailView(order Order) string {
	view := titleStyle.Render(fmt.Sprintf("Order #%d Details", order.ID)) + "\n\n"
	view += fmt.Sprintf("Type: %s\n", order.Type)
	view += fmt.Sprintf("Status: %s\n", order.Status)
	view += fmt.Sprintf("Priority: %d\n", order.Priority)
	view += fmt.Sprintf("Received: %s\n", order.TimeReceived.Format(time.RFC1123))
	if !order.TimeCompleted.IsZero() {
		view += fmt.Sprintf("Completed: %s\n", order.TimeCompleted.Format(time.RFC1123))
	}
	if order.AssignedTo != "" {
		view += fmt.Sprintf("Assigned To: %s\n", order.AssignedTo)
	}

	view += "\nItems:\n"
	for i, item := range order.Items {
		view += fmt.Sprintf("%d. %s (x%d) - %s\n", i+1, item.Name, item.Quantity, item.Status)
		if item.Notes != "" {
			view += fmt.Sprintf("   Notes: %s\n", item.Notes)
		}
	}

	view += "\nPress 'c' to cancel/complete the order, 'enter' to go back to list"

	return view
}

// createOrderView shows the current state of an order being created
func createOrderView(order Order) string {
	view := fmt.Sprintf("Order Type: %s\n", order.Type)
	view += fmt.Sprintf("Priority: %d\n\n", order.Priority)

	view += "Items:\n"
	if len(order.Items) == 0 {
		view += "No items added yet\n"
	} else {
		for i, item := range order.Items {
			view += fmt.Sprintf("%d. %s (x%d)\n", i+1, item.Name, item.Quantity)
			if item.Notes != "" {
				view += fmt.Sprintf("   Notes: %s\n", item.Notes)
			}
		}
	}

	return view
}

// startPlayground launches the LLM Playground server
func startPlayground() tea.Cmd {
	return func() tea.Msg {
		// This would start the playground server in a real implementation
		// For now, just return a message with instructions
		return confirmMsg{message: "LLM Playground server started on http://localhost:8090"}
	}
}

func main() {
	p := tea.NewProgram(initialModel())
	if _, err := p.Run(); err != nil {
		fmt.Printf("Error running program: %v", err)
		os.Exit(1)
	}
}

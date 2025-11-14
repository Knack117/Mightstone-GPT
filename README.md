# Mightstone GPT Webservice

A modern MTG Commander deckbuilding API built with **Mightstone** as the backbone, designed to power custom GPTs with comprehensive Magic: The Gathering data and analysis capabilities.

## 🚀 Features

### Core Functionality
- **Commander Data**: Comprehensive commander information and deck analysis
- **Average Decks**: EDHREC average deck fetching with multiple brackets
- **Budget Analysis**: Budget vs expensive deck comparisons
- **Card Search**: Powerful Scryfall search with full syntax support
- **Theme Data**: EDHREC theme and tag integration
- **Deck Analysis**: Automated deck analysis and recommendations

### Modern Architecture
- **Mightstone Backend**: Built on the official Mightstone package for MTG data
- **FastAPI**: High-performance async API with automatic documentation
- **Type Safety**: Full Pydantic model validation
- **Rate Limiting**: Respectful API usage with built-in rate limiting
- **Health Monitoring**: Built-in health checks and monitoring

### EDHREC Integration
- **Average Decks**: Support for all deck brackets (exhibition, core, upgraded, optimized, cedh)
- **Budget Comparisons**: Side-by-side budget vs expensive deck analysis
- **Theme Data**: Access to EDHREC theme and tag information
- **Commander Pages**: Commander-specific data and recommendations

### Scryfall Integration  
- **Card Search**: Full Scryfall search syntax support
- **Card Details**: Complete card information and images
- **Auto-complete**: Card name suggestions
- **Random Cards**: Discover random cards with filters

## 🛠️ Quick Start

### Prerequisites
- Python 3.11+
- pip or poetry

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Knack117/Mightstone-GPT.git
   cd Mightstone-GPT
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python -m app.main
   ```

The API will be available at `http://localhost:8080`

### Docker Deployment

1. **Using Docker Compose** (recommended)
   ```bash
   docker-compose up -d
   ```

2. **Using Docker directly**
   ```bash
   docker build -t mightstone-gpt .
   docker run -p 8080:8080 mightstone-gpt
   ```

## 📡 API Documentation

### Interactive Documentation
- **Swagger UI**: `http://localhost:8080/docs`
- **ReDoc**: `http://localhost:8080/redoc`

### Base URL
```
http://localhost:8080
```

### Key Endpoints

#### Health & Info
- `GET /` - Service information
- `GET /health` - Health check
- `GET /privacy` - Privacy policy

#### Commander Data
- `GET /commander/{commander_name}` - Get commander data with deck
- `GET /commander/{commander_name}/deck` - Get average deck
- `GET /commander/{commander_name}/budget-comparison` - Budget analysis

#### Card Search
- `GET /cards/search` - Search cards with Scryfall syntax
- `GET /cards/{card_name}` - Get card details

#### EDHREC Themes
- `GET /themes/{theme_name}` - Get theme data
- `GET /themes/suggestions?commander_name={name}` - Get suggestions

#### Deck Analysis
- `POST /deck/analyze` - Analyze deck list
- `GET /recommendations/{commander_name}` - Get recommendations

### Example Usage

#### Get Commander Data
```bash
curl "http://localhost:8080/commander/Sol%20Ring?bracket=optimized"
```

#### Search Cards
```bash
curl "http://localhost:8080/cards/search?q=type:creature%20cmc:3"
```

#### Get Average Deck
```bash
curl "http://localhost:8080/commander/Akiri%2C%20Line-Slinger/deck?bracket=cedh"
```

#### Budget Comparison
```bash
curl "http://localhost:8080/commander/Rakdos%2C%20Lord%20of%20Riots/budget-comparison"
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | Server port |
| `LOGLEVEL` | `INFO` | Logging level |
| `MIGHTSTONE_UA` | `Mightstone-GPT/2.0` | User agent string |
| `PRIVACY_CONTACT_EMAIL` | `pommnetwork@gmail.com` | Contact email |

### Example Configuration
```bash
export PORT=8080
export LOGLEVEL=DEBUG
export MIGHTSTONE_UA="MyApp/1.0"
```

## 🏗️ Architecture

### Service Layer
- **MightstoneService**: Core MTG data access using Mightstone
- **EDHRECService**: EDHREC data fetching and processing
- **ScryfallService**: Scryfall card search and details

### Handler Layer
- **AverageDeckHandler**: Average deck operations
- **BudgetComparisonHandler**: Budget analysis functionality

### API Layer
- **FastAPI Application**: Main API server
- **Pydantic Models**: Data validation and serialization
- **CORS Middleware**: Cross-origin resource sharing

### Utilities
- **Commander Identity**: Name normalization and color handling
- **Rate Limiting**: Respectful API usage

## 🧪 Testing

### Manual Testing
```bash
# Health check
curl http://localhost:8080/health

# Service info
curl http://localhost:8080/

# Example commander data
curl "http://localhost:8080/commander/Atraxa%2C%20Praetors%27Voice"
```

### API Testing Tools
- **Postman/Insomnia**: Import the OpenAPI spec from `/openapi.json`
- **curl**: Test individual endpoints
- **Swagger UI**: Interactive testing at `/docs`

## 🔗 Integration with Custom GPTs

### Tool Integration
The service provides a comprehensive set of tools for GPT integration:

```python
# Available tools
"scryfall_search": Search cards with advanced syntax
"commander_deck": Get average deck for commander
"budget_comparison": Compare budget vs expensive builds
"theme_data": Get EDHREC theme information
"deck_analysis": Analyze deck lists
```

### GPT Configuration
```json
{
  "functions": [
    {
      "name": "search_mtg_cards",
      "description": "Search for MTG cards using Scryfall syntax",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {"type": "string"},
          "limit": {"type": "integer"}
        }
      }
    }
  ]
}
```

## 🚀 Deployment

### Render.com (Recommended)
1. Connect your GitHub repository
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `python -m app.main`
4. Configure environment variables

### Railway
1. Connect repository
2. Auto-deploy enabled
3. Set environment variables

### Heroku
1. Create `Procfile`: `web: python -m app.main`
2. Set environment variables
3. Deploy via git

### Self-Hosted
```bash
# Using gunicorn
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Using systemd service
sudo systemctl enable mightstone-gpt
sudo systemctl start mightstone-gpt
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Mightstone** - Comprehensive MTG data package
- **Scryfall** - MTG card database API
- **EDHREC** - Commander deck statistics
- **FastAPI** - Modern Python web framework

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/Knack117/Mightstone-GPT/issues)
- **Email**: pommnetwork@gmail.com
- **Documentation**: `/docs` endpoint when running

## 📊 Status

- ✅ **Mightstone Integration** - Core functionality implemented
- ✅ **EDHREC Service** - Average decks and themes
- ✅ **Scryfall Service** - Card search and details
- ✅ **FastAPI Application** - Full REST API
- ✅ **Docker Support** - Containerized deployment
- 🔄 **Advanced Analysis** - Enhanced deck analysis (in progress)
- 🔄 **Caching Layer** - Performance optimization (planned)

---

**Built with ❤️ for the MTG community**
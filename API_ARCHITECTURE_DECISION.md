# API Architecture Decision Document

**Date:** February 3, 2026  
**Project:** Utility Billing AI System  
**Decision:** Server-Side Rendering (SSR) vs REST API Architecture

---

## ⚠️ IMPORTANT: Current Implementation Status

**CURRENT STATE:** System is using **Streamlit** (`app/streamlit_app.py`)  
**CHOSEN APPROACH:** Server-Side Rendering (SSR) with **FastAPI** (NOT YET IMPLEMENTED)  
**STATUS:** Decision made, implementation pending

This document describes the **chosen architecture** for future implementation, not the current system.

---

## Table of Contents
1. [Chosen Architecture](#chosen-architecture)
2. [Alternative Approach](#alternative-approach)
3. [Detailed Comparison](#detailed-comparison)
4. [Implementation Examples](#implementation-examples)
5. [When to Switch](#when-to-switch)
6. [Migration Path](#migration-path)

---

## Chosen Architecture

### **Server-Side Rendering (SSR) with FastAPI**

We have **chosen** to implement a **monolithic page-based architecture** where each route returns a fully-rendered HTML page with data already populated.

> **Note:** This is the planned architecture. Current implementation still uses Streamlit.

#### Architecture Pattern (Planned)
```
Browser Request → FastAPI Route → Database Utilities → Template Rendering → HTML Response
```

#### Key Characteristics (When Implemented)
- **Single endpoint per page** (e.g., `/tariffs`, `/user-bills`)
- **Backend renders HTML** using Jinja2 templates
- **Data fetched on server-side** before sending response
- **Full page loads** on every interaction
- **Minimal JavaScript** required on frontend

#### Planned Implementation Structure
```python
@app.get("/tariffs", response_class=HTMLResponse)
async def tariffs_page(request: Request):
    # Fetch all data needed for the page
    sc_codes = get_distinct_sc_codes()
    
    # Render complete HTML with data embedded
    return templates.TemplateResponse("tariffs.html", {
        "request": request,
        "sc_codes": sc_codes
    })
```

#### Why This Was Chosen

1. **Simplicity**
   - Fewer endpoints to maintain
   - No need for complex frontend JavaScript frameworks
   - Easier to debug (single request = single response)

2. **Speed of Development**
   - Quick to implement
   - Leverages existing database utilities directly
   - No API design or versioning needed

3. **Use Case Fit**
   - Internal tool for billing department
   - Limited number of concurrent users
   - No mobile app requirements
   - No third-party integrations planned

4. **Team Capability**
   - Works with basic HTML/CSS skills
   - No frontend framework expertise required
   - Backend developers can maintain full stack

5. **Performance**
   - Fast initial page load (data already in HTML)
   - No extra round-trip for data fetching
   - Good for SEO (if needed in future)

---

## Alternative Approach

### **REST API with Client-Side Rendering (CSR)**

The alternative is to create **individual API endpoints** for each utility function, returning JSON data, and using JavaScript on the frontend to fetch and display data dynamically.

#### Architecture Pattern
```
Browser Request → Static HTML Shell → JavaScript → Multiple API Calls → JSON Responses → DOM Manipulation
```

#### Key Characteristics
- **Multiple granular endpoints** (e.g., `/api/tariffs/sc-codes`, `/api/tariffs/versions/{sc_code}`)
- **Backend returns JSON** instead of HTML
- **Frontend JavaScript** fetches data and updates DOM
- **Partial page updates** without full reload
- **Decoupled frontend/backend**

#### Alternative Implementation Structure

##### Backend (FastAPI)
```python
# API Endpoints returning JSON
@app.get("/api/tariffs/sc-codes")
async def get_sc_codes():
    """Get list of all service class codes"""
    return {"sc_codes": get_distinct_sc_codes()}

@app.get("/api/tariffs/versions/{sc_code}")
async def get_versions(sc_code: str):
    """Get all versions for a specific SC code"""
    return {"versions": get_versions_for_sc(sc_code)}

@app.get("/api/tariffs/logic")
async def get_tariff_logic(sc_code: str, version: str):
    """Get tariff logic for specific SC code and version"""
    logic = get_logic_for_sc_version(sc_code, version)
    return {"logic": logic}

# Page route returns empty HTML shell
@app.get("/tariffs", response_class=HTMLResponse)
async def tariffs_page(request: Request):
    return templates.TemplateResponse("tariffs.html", {
        "request": request
    })
```

##### Frontend (JavaScript)
```html
<!-- tariffs.html -->
<!DOCTYPE html>
<html>
<body>
    <select id="sc-code-select">
        <!-- Populated dynamically -->
    </select>
    
    <script>
        // Fetch SC codes on page load
        async function loadScCodes() {
            const response = await fetch('/api/tariffs/sc-codes');
            const data = await response.json();
            
            const select = document.getElementById('sc-code-select');
            data.sc_codes.forEach(code => {
                const option = document.createElement('option');
                option.value = code;
                option.text = code;
                select.appendChild(option);
            });
        }
        
        // Load versions when SC code selected
        async function loadVersions(scCode) {
            const response = await fetch(`/api/tariffs/versions/${scCode}`);
            const data = await response.json();
            // Update DOM with versions...
        }
        
        // Initialize
        loadScCodes();
    </script>
</body>
</html>
```

---

## Detailed Comparison

### Comparison Table

| Aspect | SSR (Current) | REST API (Alternative) |
|--------|---------------|------------------------|
| **Complexity** | Low | High |
| **Frontend JavaScript** | Minimal | Heavy |
| **Initial Page Load** | Fast (data included) | Slower (shell + API calls) |
| **Subsequent Updates** | Slow (full page reload) | Fast (partial updates) |
| **API Reusability** | None | High |
| **SEO Friendly** | Yes | No (without extra work) |
| **Mobile App Support** | No | Yes |
| **Development Speed** | Fast | Moderate |
| **Maintenance** | Simple | Complex |
| **Debugging** | Easy | Moderate |
| **Network Requests** | 1 per page | Multiple per interaction |
| **State Management** | Server-side (simple) | Client-side (complex) |
| **Real-time Updates** | Difficult | Easy |
| **Offline Capability** | No | Possible with caching |
| **Third-party Integration** | Difficult | Easy |
| **Team Skill Required** | Backend + Basic HTML | Full-stack + JavaScript |

---

### Detailed Pros and Cons

#### Server-Side Rendering (Current Choice)

##### Advantages ✅

1. **Simplicity**
   - One endpoint handles all logic for a page
   - No need to coordinate multiple API calls
   - Easier mental model: request → response

2. **Performance (Initial Load)**
   - Single request gets everything
   - No "loading spinners" or blank screens
   - Faster Time to First Contentful Paint (FCP)

3. **SEO Optimization**
   - Search engines can easily crawl content
   - All data visible in page source
   - Better for public-facing pages

4. **Less JavaScript**
   - Works with JavaScript disabled
   - Smaller bundle sizes
   - Fewer browser compatibility issues

5. **Easier Debugging**
   - View source shows all data
   - Network tab shows single request
   - No async race conditions

6. **Security**
   - Data stays on server until rendered
   - Less exposed API surface area
   - Easier to implement CSRF protection

##### Disadvantages ❌

1. **Full Page Reloads**
   - Every interaction requires page refresh
   - Loses scroll position
   - Poor user experience for frequent updates

2. **Tight Coupling**
   - Frontend and backend tightly connected
   - Can't separate teams easily
   - Frontend changes require backend deployments

3. **No API Reusability**
   - Can't build mobile app without duplication
   - CLI tools can't use same endpoints
   - Third-party integrations difficult

4. **Server Load**
   - Server does all rendering work
   - More CPU usage per request
   - Harder to scale horizontally

5. **Limited Interactivity**
   - Real-time updates difficult
   - Dynamic filtering requires page reload
   - Can't do smooth animations/transitions

---

#### REST API with Client-Side Rendering

##### Advantages ✅

1. **API Reusability**
   - Mobile apps use same endpoints
   - CLI tools can query data
   - Third-party integrations possible
   - Microservices can consume APIs

2. **Better User Experience (After Initial Load)**
   - Partial page updates
   - No page flicker
   - Smooth transitions
   - Real-time updates possible

3. **Separation of Concerns**
   - Frontend and backend completely decoupled
   - Teams can work independently
   - Frontend can be replaced without backend changes
   - Different frontends can use same API (web, mobile, desktop)

4. **Scalability**
   - API servers and frontend can scale independently
   - Can use CDN for static files
   - Caching strategies more flexible

5. **Modern Developer Experience**
   - Works with React, Vue, Angular
   - Component-based architecture
   - Hot module replacement in development

6. **Offline Capabilities**
   - Can cache API responses
   - Service workers for offline mode
   - Progressive Web App (PWA) possible

##### Disadvantages ❌

1. **Complexity**
   - More endpoints to maintain
   - Need API versioning strategy
   - More moving parts to debug

2. **More JavaScript**
   - Larger bundle sizes
   - Browser compatibility concerns
   - JavaScript required for functionality

3. **Slower Initial Load**
   - HTML shell loads first
   - Then JavaScript loads
   - Then API calls fetch data
   - Multiple round-trips

4. **SEO Challenges**
   - Search engines may not see dynamic content
   - Need Server-Side Rendering (SSR) or Static Site Generation (SSG)
   - More complex setup for SEO

5. **State Management**
   - Need to manage client-side state
   - Cache invalidation complexity
   - Sync issues between client and server

6. **Development Overhead**
   - Need to design API structure
   - API documentation required
   - More testing needed (API + frontend)

7. **Security Concerns**
   - More endpoints = larger attack surface
   - CORS configuration needed
   - JWT/token management required

---

## Implementation Examples

### Example 1: User Bills Page

#### Current SSR Approach
```python
# Backend: src/api/main.py
@app.get("/user-bills", response_class=HTMLResponse)
async def user_bills_page(
    request: Request, 
    account: Optional[str] = None
):
    """Single endpoint that does everything"""
    # Get all accounts for dropdown
    accounts = fetch_all_account_numbers()
    
    # Get bills (filtered if account provided)
    bills = fetch_user_bills(account) if account else []
    
    # Render complete page with all data
    return templates.TemplateResponse("user_bills.html", {
        "request": request,
        "accounts": accounts,
        "bills": bills,
        "selected_account": account
    })
```

```html
<!-- Frontend: templates/user_bills.html -->
<form method="get" action="/user-bills">
    <select name="account">
        {% for acc in accounts %}
            <option value="{{ acc }}" 
                {% if acc == selected_account %}selected{% endif %}>
                {{ acc }}
            </option>
        {% endfor %}
    </select>
    <button type="submit">Filter</button>
</form>

<table>
    {% for bill in bills %}
        <tr>
            <td>{{ bill.account_number }}</td>
            <td>{{ bill.amount }}</td>
        </tr>
    {% endfor %}
</table>
```

**User Experience:**
1. User visits `/user-bills` → sees page with dropdown
2. User selects account and clicks "Filter"
3. **Full page reloads** → URL changes to `/user-bills?account=12345`
4. Server fetches data and renders new page
5. User sees filtered results

---

#### Alternative REST API Approach
```python
# Backend: src/api/main.py

# API Endpoints
@app.get("/api/user-bills/accounts")
async def get_accounts():
    """Get all account numbers"""
    return {
        "accounts": fetch_all_account_numbers()
    }

@app.get("/api/user-bills")
async def get_bills(account: Optional[str] = None):
    """Get bills, optionally filtered by account"""
    bills = fetch_user_bills(account) if account else []
    return {
        "bills": [
            {
                "id": bill.id,
                "account_number": bill.account_number,
                "amount": float(bill.amount),
                "billing_date": bill.billing_date.isoformat()
            }
            for bill in bills
        ]
    }

# Page route - just returns HTML shell
@app.get("/user-bills", response_class=HTMLResponse)
async def user_bills_page(request: Request):
    return templates.TemplateResponse("user_bills.html", {
        "request": request
    })
```

```html
<!-- Frontend: templates/user_bills.html -->
<div id="app">
    <select id="account-select">
        <option value="">Loading...</option>
    </select>
    <button onclick="filterBills()">Filter</button>
    
    <div id="loading" style="display:none;">Loading...</div>
    <table id="bills-table">
        <thead>
            <tr><th>Account</th><th>Amount</th></tr>
        </thead>
        <tbody id="bills-body">
            <!-- Populated by JavaScript -->
        </tbody>
    </table>
</div>

<script>
    let accounts = [];
    let bills = [];
    
    // Load accounts on page load
    async function loadAccounts() {
        const response = await fetch('/api/user-bills/accounts');
        const data = await response.json();
        accounts = data.accounts;
        
        const select = document.getElementById('account-select');
        select.innerHTML = '<option value="">All Accounts</option>';
        accounts.forEach(acc => {
            const option = document.createElement('option');
            option.value = acc;
            option.text = acc;
            select.appendChild(option);
        });
    }
    
    // Filter bills by account
    async function filterBills() {
        const account = document.getElementById('account-select').value;
        const loading = document.getElementById('loading');
        
        loading.style.display = 'block';
        
        const url = account 
            ? `/api/user-bills?account=${account}`
            : '/api/user-bills';
            
        const response = await fetch(url);
        const data = await response.json();
        bills = data.bills;
        
        renderBills();
        loading.style.display = 'none';
    }
    
    // Render bills in table
    function renderBills() {
        const tbody = document.getElementById('bills-body');
        tbody.innerHTML = '';
        
        bills.forEach(bill => {
            const row = tbody.insertRow();
            row.insertCell(0).textContent = bill.account_number;
            row.insertCell(1).textContent = `$${bill.amount}`;
        });
    }
    
    // Initialize
    loadAccounts();
</script>
```

**User Experience:**
1. User visits `/user-bills` → sees loading state
2. JavaScript fetches accounts → dropdown populated
3. User selects account and clicks "Filter"
4. **Only table updates** (no page reload)
5. Shows loading spinner while fetching
6. Table updates with new data

---

### Example 2: Variable Tariff Rates Query

#### Current SSR Approach
```python
@app.get("/rates", response_class=HTMLResponse)
async def rates_page(
    request: Request,
    sc_code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Single endpoint handles form and results"""
    rates = None
    
    if sc_code and start_date and end_date:
        # Determine table from SC code
        table = determine_table_from_sc(sc_code)
        
        # Fetch rates
        rates = fetch_rates_for_dates(
            table_name=table,
            sc_code=sc_code,
            effective_dates=[start_date, end_date]
        )
    
    return templates.TemplateResponse("rates.html", {
        "request": request,
        "rates": rates,
        "sc_code": sc_code,
        "start_date": start_date,
        "end_date": end_date
    })
```

#### Alternative REST API Approach
```python
# Endpoint to determine which table a SC code belongs to
@app.get("/api/rates/table/{sc_code}")
async def get_rate_table(sc_code: str):
    """Determine which table (SBC/TRA/RDM/RAM) for SC code"""
    table = determine_table_from_sc(sc_code)
    return {"table": table}

# Endpoint to fetch rates
@app.get("/api/rates")
async def get_rates(
    table: str,
    sc_code: str,
    start_date: str,
    end_date: str
):
    """Fetch rates for date range"""
    rates = fetch_rates_for_dates(
        table_name=table,
        sc_code=sc_code,
        effective_dates=[start_date, end_date]
    )
    
    return {
        "rates": [
            {
                "effective_date": rate.effective_date.isoformat(),
                "rate": float(rate.rate)
            }
            for rate in rates
        ]
    }
```

---

## When to Switch

### Triggers for Moving to REST API Architecture

Consider switching to REST API approach when:

#### 1. **Mobile App Development**
- Need native iOS/Android app
- Want to reuse backend logic
- Can't duplicate database utilities

**Example:** Building a mobile app for field technicians to view bills on-site.

#### 2. **Third-Party Integrations**
- Partners need to query your data
- Building B2B integrations
- Need webhook consumers

**Example:** Utility company wants to integrate with your billing data for their dashboard.

#### 3. **Microservices Architecture**
- Multiple services need same data
- Building service mesh
- Want to decouple services

**Example:** Separate invoice generation service needs to fetch tariff rates.

#### 4. **Real-Time Requirements**
- Need live data updates
- WebSocket or Server-Sent Events (SSE)
- Collaborative features

**Example:** Multiple users monitoring pipeline runs simultaneously with live status updates.

#### 5. **Performance at Scale**
- Heavy traffic (1000+ concurrent users)
- Need to cache responses aggressively
- Want to use CDN for API responses

**Example:** Public portal for customers to check bills.

#### 6. **Modern Frontend Framework**
- Team wants React/Vue/Angular
- Need complex UI interactions
- Building Single Page Application (SPA)

**Example:** Dashboard with drag-and-drop, inline editing, complex filtering.

#### 7. **CLI Tools or Scripts**
- Need programmatic access
- Building automation tools
- Want to script operations

**Example:** Automated billing reports generated by cron jobs.

---

### Signs to Stay with SSR

Keep the current SSR approach when:

1. **Internal Tool Only** - No external integrations planned
2. **Small User Base** - < 50 concurrent users
3. **Simple CRUD Operations** - Basic create, read, update, delete
4. **Team Prefers Backend** - No frontend JavaScript expertise
5. **Fast Development** - Need to ship quickly
6. **SEO Important** - Content needs to be searchable

---

## Migration Path

If you decide to switch to REST API in the future, here's the migration strategy:

### Phase 1: Add API Endpoints (No Breaking Changes)
```python
# Keep existing SSR routes
@app.get("/user-bills", response_class=HTMLResponse)
async def user_bills_page(request: Request):
    # Existing implementation
    pass

# Add new API routes alongside
@app.get("/api/v1/user-bills")
async def api_get_user_bills(account: Optional[str] = None):
    # Reuse same utility functions
    bills = fetch_user_bills(account) if account else []
    return {"bills": bills}
```

### Phase 2: Migrate One Page at a Time
Convert one page to use API endpoints while keeping others as SSR.

```html
<!-- user_bills.html - now uses API -->
<script>
    fetch('/api/v1/user-bills')
        .then(r => r.json())
        .then(data => renderBills(data.bills));
</script>
```

### Phase 3: Deprecate Old Routes
Once all pages use API endpoints, mark old SSR routes as deprecated.

```python
@app.get("/user-bills-old", response_class=HTMLResponse, deprecated=True)
async def old_user_bills_page(request: Request):
    # Keep for backward compatibility
    pass
```

### Phase 4: Remove SSR Routes
After ensuring no clients use old routes, remove them.

---

## Hybrid Approach (Best of Both Worlds)

You can also implement a **hybrid architecture**:

```python
# API endpoints for data
@app.get("/api/user-bills")
async def api_get_bills(account: Optional[str] = None):
    return {"bills": fetch_user_bills(account)}

# SSR page that can optionally use API
@app.get("/user-bills", response_class=HTMLResponse)
async def user_bills_page(
    request: Request,
    account: Optional[str] = None,
    format: Optional[str] = None
):
    # If format=json, return API response
    if format == "json":
        return api_get_bills(account)
    
    # Otherwise, render HTML
    bills = fetch_user_bills(account)
    return templates.TemplateResponse("user_bills.html", {...})
```

### Benefits
- API endpoints available for future needs
- Pages still work with SSR
- Gradual migration possible
- No breaking changes

### Drawbacks
- More code to maintain
- Two ways to do same thing
- Potential duplication

---

## Recommendation

### For Your Current Use Case

**✅ Stick with Server-Side Rendering (SSR)**

**Reasons:**
1. Internal tool for billing department only
2. Team has backend expertise, limited frontend skills
3. No mobile app or third-party integration requirements
4. Simple CRUD operations sufficient
5. Fast development and deployment more important
6. Small user base (< 50 users)

### Future Considerations

**✋ Consider REST API when:**
- Building mobile app for field access
- Need to integrate with external utility company systems
- User base grows to > 100 concurrent users
- Requirement for real-time bill monitoring
- Team gains React/Vue expertise

### Transition Timeline

If migration becomes necessary:

1. **Months 1-2:** Add API endpoints alongside SSR (hybrid)
2. **Months 3-4:** Migrate dashboard page to use APIs
3. **Months 5-6:** Migrate remaining pages
4. **Month 7+:** Remove old SSR routes, full API architecture

---

## References and Further Reading

### Server-Side Rendering (SSR)
- FastAPI Jinja2 Templates: https://fastapi.tiangolo.com/advanced/templates/
- When to use SSR: https://web.dev/rendering-on-the-web/

### REST API Design
- FastAPI JSON Responses: https://fastapi.tiangolo.com/tutorial/response-model/
- REST API Best Practices: https://restfulapi.net/

### Hybrid Approaches
- Progressive Enhancement: https://developer.mozilla.org/en-US/docs/Glossary/Progressive_Enhancement
- Islands Architecture: https://jasonformat.com/islands-architecture/

---

## Document History

| Date | Author | Changes |
|------|--------|---------|
| Feb 3, 2026 | System | Initial architecture decision document created |

---

## Conclusion

**Decision Made: Server-Side Rendering (SSR) with FastAPI**

**Current Status:**
- ✅ Architecture decision finalized
- ❌ FastAPI implementation NOT yet completed
- 🔄 Currently using Streamlit (app/streamlit_app.py)
- 📋 FastAPI is commented out in requirements.txt

**Next Steps:**
1. Implement FastAPI backend in `src/api/main.py`
2. Create Jinja2 templates in `src/api/templates/`
3. Add static CSS in `src/api/static/`
4. Enable FastAPI in requirements.txt
5. Test and migrate from Streamlit

This document serves as a reference for understanding why SSR was chosen over REST API architecture for the Utility Billing AI system. The decision prioritizes simplicity, development speed, and team capabilities over advanced features that are not currently needed.

If requirements change in the future, this document provides a clear migration path to REST API architecture without disrupting existing functionality.

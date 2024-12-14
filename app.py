from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow 
from marshmallow import fields
from marshmallow import ValidationError, fields
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://root:Preciosa2016!@localhost/e_commerce_db'
db = SQLAlchemy(app)
ma = Marshmallow(app)

class CustomerSchema(ma.Schema):
    name = fields.String(required=True)
    email = fields.String(required=True)
    phone = fields.String(required=True)

    class Meta:
        fields = ("name", "email", "phone", "id")

customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)

class CustomerAccountSchema(ma.Schema):
    username = fields.String(required=True)
    password = fields.String(required=True)
    customer_id = fields.Integer(required=True)

    class Meta:
        fields = ("id", "username", "customer_id")

customer_account_schema = CustomerAccountSchema()
customer_accounts_schema = CustomerAccountSchema(many=True)

class ProductSchema(ma.Schema):
    name = fields.String(required=True)
    price = fields.Float(required=True)

    class Meta:
        fields = ("id", "name", "price")


product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

# Models
class Customer(db.Model):
    __tablename__ = 'Customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(320))
    phone = db.Column(db.String(15))
    orders = db.relationship('Order', backref='customer') # Establishing the relationship

class Order(db.Model):
    __tablename__ = 'Orders'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('Customers.id'))
    status = db.Column(db.String(50), nullable=False, default='Pending')

# One-to-One
class CustomerAccount(db.Model):
    __tablename__ = 'Customer_Accounts'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('Customers.id'))
    customer = db.relationship('Customer', backref='customer_account', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# many-to-many
order_product = db.Table('Order_Product',
        db.Column('order_id', db.Integer, db.ForeignKey('Orders.id'), primary_key = True),
        db.Column('product_id', db.Integer, db.ForeignKey('Products.id'), primary_key=True))

class Product(db.Model):
    __tablename__ = 'Products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock_level = db.Column(db.Integer,nullable=False, default=0)
    orders = db.relationship('Order', secondary=order_product, backref=db.backref('products'))

# Initializea the database and create tables
with app.app_context():
    db.create_all()

# CUSTOMER AND CUSTOMER ACCOUNT MANAGEMENT
# Create Customer
@app.route('/customers', methods=['POST'])
def add_customer():
    try:
        #Validate and deserialize input
        customer_data = customer_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400

    new_customer = Customer(name=customer_data['name'], email=customer_data['email'], phone=customer_data['phone'])
    db.session.add(new_customer)
    db.session.commit()
    return jsonify({"message": "New customer added successfully"}), 201

# Read Customer
@app.route('/customers/<int:customer_id>', methods=['GET'])
def get_customer(customer_id):
    customer = Customer.query.get(customer_id)

    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    
    customer_data = customer_schema.dump(customer)
    return jsonify(customer_data), 200

# Update Customer
@app.route('/customers/<int:id>', methods=['PUT'])
def update_customer(id):
    customer = Customer.query.get_or_404(id)
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    customer.name = customer_data['name']
    customer.email = customer_data['email']
    customer.phone = customer_data['phone']
    db.session.commit()
    return jsonify({"message": "Customer details updated successfully"}), 200

@app.route('/customers/<int:id>', methods=['DELETE'])
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    if not customer:
        return jsonify({'error': 'Customer not found'}),404

    try:
        db.session.delete(customer)
        db.session.commit()
        return jsonify({'message': f'Customer with ID {id} has been deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


# Create Customer Account
@app.route('/customer_accounts', methods=['POST'])
def create_customer_account():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    customer_id = data.get('customer_id')

    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404
    
    if CustomerAccount.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    password_hash = generate_password_hash(password)

    # Create and save new account
    new_account = CustomerAccount(username=username, password_hash=password_hash, customer_id=customer_id)
    db.session.add(new_account)
    db.session.commit()

    return jsonify({'id': new_account.id, 'username': new_account.username, 'customer_id': new_account.customer_id}), 201
           

# Retrieve Customer Account
@app.route('/customer_accounts/<int:id>', methods=["GET"])
def get_customer_account(id): 
    #Query for the customer account
    customer_account = CustomerAccount.query.get(id)
    if not customer_account:
        return jsonify({'error': 'Customer account not found'}), 404
    
    # Prepare the response data
    response = {
        'id': customer_account.id,
        'username': customer_account.username,
        'customer': {
            'id': customer_account.customer.id,
            'name': customer_account.customer.name,
            'email': customer_account.customer.email,
            'phone': customer_account.customer.phone
        }
    }
    return jsonify(response), 200

@app.route('/customer_accounts/<int:id>', methods=['PUT'])
def update_customer_account(id):
    # Fetch the customer account by ID
    customer_account = CustomerAccount.query.get(id)
    if not customer_account:
        return jsonify({'error': 'Customer account not found'}), 404

    # Parse the request data
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # Update fields if provided
    if username:
        customer_account.username = username
    if password:
        customer_account.password_hash = generate_password_hash(password)

    try:
        # Commit changes to the database
        db.session.commit()
        return jsonify({
            'message': 'Customer account updated successfully',
            'id': customer_account.id,
            'username': customer_account.username
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while updating the customer account', 'details': str(e)}), 500


@app.route('/customer_accounts/<int:id>', methods=['DELETE'])
def delete_customer_account(id):
    # Fetch the customer account by ID
    customer_account = CustomerAccount.query.get(id)
    if not customer_account:
        return jsonify({'error': 'Customer account not found'}), 404

    try:
        # Delete the account and commit changes
        db.session.delete(customer_account)
        db.session.commit()
        return jsonify({'message': f'Customer account with ID {id} has been deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while deleting the customer account', 'details': str(e)}), 500

# PRODUCT CATALOG 
# CREATE PRODUCT
@app.route('/products', methods=['POST'])
def create_product():
    try:
        # Validate and parse input data
        data = request.json
        product_data = product_schema.load(data)

        # Create a new product instance
        new_product = Product(name=product_data['name'], price=product_data['price'])

        # Add the product to the database
        db.session.add(new_product)
        db.session.commit()

        # Return the created product's details
        return product_schema.jsonify(new_product), 201
    except ValidationError as e:
        return jsonify({'error': 'Validate Error', 'messages': e.messages}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while creating the product', 'details': str(e)}), 500


# READ PRODUCT
@app.route('/products/<int:id>', methods=['GET'])
def read_product(id):
    product = Product.query.get(id)
    if not product:
        return jsonify({"error": "Product not found"}), 401
    return jsonify({"id": product.id, "name": product.name, "price": product.price}), 200

# Update Product
@app.route('/products/<int:id>', methods=['PUT'])
def update_product(id):
    data = request.get_json()
    product = Product.query.get(id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    product.name = data.get('name', product.name)
    product.price = data.get('price', product.price)
    db.session.commit()
    return jsonify({"message": "Product updated successfully", "product": {"id": product.id, "name": product.name, "price": product.price}}), 200
    
# DELETE PRODUCT
@app.route('/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    product = Product.query.get(id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted successfully"}), 200

# LIST PRODUCTS
@app.route('/products', methods=['GET'])
def list_products():
    products = Product.query.all()
    product_list = [{"id": p.id, "name": p.name, "price": p.price} for p in products]
    return jsonify({"products": product_list}), 200

# VIEW AND MANAGE PRODUCT STOCK LEVELS 
@app.route('/products/<int:id>/stock', methods=['GET'])
def view_stock(id):
    product = Product.query.get(id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify({"id": product.id, "stock_level": product.stock_level}), 200

# UPDATE STOCK LEVELS
@app.route('/products/<int:id>/stock', methods=['PUT'])
def update_stock(id):
    data = request.get_json()
    product = Product.query.get(id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    product.stock_level = data.get('stock_level', product.stock_level)
    db.session.commit()
    return jsonify({"message": "Stock level updated", "product": {"id": product.id, "stock_level": product.stock_level}}), 200

# RESTOCK PRODUCTS WHEN LOW 
@app.route('/products/restock', methods=['POST'])
def restock_products():
    threshold = request.json.get('threshold', 10)
    restock_amount = request.json.get('restock_amount', 20)

    products = Product.query.filter(Product.stock_level < threshold).all()
    if not products:
        return jsonify({"message": "No products below the threshold"}), 200

    for product in products:
        product.stock_level += restock_amount
    db.session.commit()

    restocked_products = [{"id": p.id, "name": p.name, "stock_level": p.stock_level} for p in products]
    return jsonify({"message": "Products restocked", "restocked_products": restocked_products}), 200

# ORDER PROCESSING
# PLACE ORDER
@app.route('/orders', methods=['POST'])
def place_order():
    data = request.json
    customer_id = data.get('customer_id')
    product_ids = data.get('product_ids')

    if not customer_id or not product_ids:
        return jsonify({"error": "Customer ID and Product Ids are required"}), 400
    
    try:
        new_order = Order(date=date.today(), customer_id=customer_id)
        db.session.add(new_order)
        db.session.flush()

        for product_id in product_ids:
            product = Product.query.get(product_id)
            if product is None:
                return jsonify({"error": f"Product with ID {product_id} not found"}), 404
            order_product_association = order_product.insert().values(order_id=new_order.id, product_id=product_id)
            db.session.execute(order_product_association)
        
        db.session.commit()
        return jsonify({"message": "Order placed successfully", "order_id": new_order.id}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# RETRIEVE ORDER
@app.route('/orders/<int:order_id>', methods=['GET'])
def retrieve_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    products = [
        {"id": product.id, "name": product.name, "price": product.price}
        for product in order.products
    ]
    return jsonify({
        "order_id": order.id,
        "order_date": order.date,
        "customer": {"id": order.customer.id, "name": order.customer.name},
        "products": products
    }), 200

# TRACK ORDER
@app.route('/orders/<int:order_id>/track', methods=['GET'])
def track_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    return jsonify({
        "order_id": order.id,
        "order_date": order.date,
        "status": "Processing",  # Example status
        "expected_delivery": "2024-12-20"  # Replace with actual logic
    }), 200


# MANAGE ORDER HISTORY
@app.route('/customers/<int:customer_id>/orders', methods=['GET'])
def manage_order_history(customer_id):
    orders = Order.query.filter_by(customer_id=customer_id).all()
    if not orders:
        return jsonify({"message": "No orders found for this customer"}), 404

    order_history = [
        {
            "order_id": order.id,
            "order_date": order.date,
            "products": [{"id": product.id, "name": product.name, "price": product.price} for product in order.products]
        }
        for order in orders
    ]
    return jsonify({"order_history": order_history}), 200



# CANCEL ORDER
@app.route('/orders/<int:order_id>/cancel', methods=['PUT'])
def cancel_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    # Example condition for cancelling
    if order.status == "Shipped":
        return jsonify({"error": "Order cannot be cancelled as it has been shipped"}), 400
    
    try:
        order.status = "Cancelled"
        db.session.commit()
        return jsonify({"message": "Order canceled successfull"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# CALCULATE ORDER TOTAL PRICE
@app.route('/orders/<int:order_id>/total', methods=['GET'])
def calculate_order_total(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    total_price = sum(product.price for product in order.products)
    return jsonify({"order_id": order.id, "total_price": total_price}), 200



if __name__ == '__main__':
    app.run(debug=True)
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title ContentRegistry
 * @dev Smart contract for registering and verifying digital content ownership
 * @author Authx Platform
 * 
 * Patent-pending technology for blockchain-based content authenticity verification
 */
contract ContentRegistry {
    
    struct ContentRecord {
        string sha256Hash;
        address owner;
        string ownerName;
        string contentType;
        uint256 timestamp;
        bool exists;
    }
    
    // Mapping from SHA-256 hash to content record
    mapping(string => ContentRecord) public contentRegistry;
    
    // Mapping from owner address to their content hashes
    mapping(address => string[]) public ownerContent;
    
    // Array of all registered hashes (for enumeration)
    string[] public allContentHashes;
    
    // Events
    event ContentRegistered(
        string indexed sha256Hash,
        address indexed owner,
        string ownerName,
        string contentType,
        uint256 timestamp
    );
    
    event OwnershipTransferred(
        string indexed sha256Hash,
        address indexed previousOwner,
        address indexed newOwner,
        uint256 timestamp
    );
    
    /**
     * @dev Register new content on the blockchain
     * @param _sha256Hash SHA-256 hash of the content
     * @param _ownerName Name of the content creator
     * @param _contentType Type of content (image, audio, text, etc.)
     */
    function registerContent(
        string memory _sha256Hash,
        string memory _ownerName,
        string memory _contentType
    ) public returns (bool) {
        require(bytes(_sha256Hash).length > 0, "Hash cannot be empty");
        require(!contentRegistry[_sha256Hash].exists, "Content already registered");
        
        // Create content record
        contentRegistry[_sha256Hash] = ContentRecord({
            sha256Hash: _sha256Hash,
            owner: msg.sender,
            ownerName: _ownerName,
            contentType: _contentType,
            timestamp: block.timestamp,
            exists: true
        });
        
        // Add to owner's content list
        ownerContent[msg.sender].push(_sha256Hash);
        
        // Add to global registry
        allContentHashes.push(_sha256Hash);
        
        emit ContentRegistered(
            _sha256Hash,
            msg.sender,
            _ownerName,
            _contentType,
            block.timestamp
        );
        
        return true;
    }
    
    /**
     * @dev Get content details by hash
     * @param _sha256Hash SHA-256 hash of the content
     * @return exists Whether content exists
     * @return owner Address of the owner
     * @return ownerName Name of the owner
     * @return contentType Type of content
     * @return timestamp Registration timestamp
     */
    function getContent(string memory _sha256Hash) 
        public 
        view 
        returns (
            bool exists,
            address owner,
            string memory ownerName,
            string memory contentType,
            uint256 timestamp
        ) 
    {
        ContentRecord memory record = contentRegistry[_sha256Hash];
        return (
            record.exists,
            record.owner,
            record.ownerName,
            record.contentType,
            record.timestamp
        );
    }
    
    /**
     * @dev Verify if content is registered and owned by specific address
     * @param _sha256Hash SHA-256 hash of the content
     * @param _owner Address to verify ownership
     * @return isOwner Whether the address is the owner
     */
    function verifyOwnership(string memory _sha256Hash, address _owner) 
        public 
        view 
        returns (bool isOwner) 
    {
        ContentRecord memory record = contentRegistry[_sha256Hash];
        return record.exists && record.owner == _owner;
    }
    
    /**
     * @dev Get all content registered by an owner
     * @param _owner Address of the owner
     * @return Array of SHA-256 hashes
     */
    function getOwnerContent(address _owner) 
        public 
        view 
        returns (string[] memory) 
    {
        return ownerContent[_owner];
    }
    
    /**
     * @dev Transfer content ownership (with original owner consent)
     * @param _sha256Hash SHA-256 hash of the content
     * @param _newOwner Address of the new owner
     * @param _newOwnerName Name of the new owner
     */
    function transferOwnership(
        string memory _sha256Hash,
        address _newOwner,
        string memory _newOwnerName
    ) public returns (bool) {
        ContentRecord storage record = contentRegistry[_sha256Hash];
        require(record.exists, "Content not found");
        require(record.owner == msg.sender, "Only owner can transfer");
        require(_newOwner != address(0), "Invalid new owner address");
        
        address previousOwner = record.owner;
        
        // Update owner
        record.owner = _newOwner;
        record.ownerName = _newOwnerName;
        
        // Add to new owner's list
        ownerContent[_newOwner].push(_sha256Hash);
        
        emit OwnershipTransferred(
            _sha256Hash,
            previousOwner,
            _newOwner,
            block.timestamp
        );
        
        return true;
    }
    
    /**
     * @dev Get total number of registered content
     * @return Total count
     */
    function getTotalRegistered() public view returns (uint256) {
        return allContentHashes.length;
    }
    
    /**
     * @dev Check if content exists in registry
     * @param _sha256Hash SHA-256 hash of the content
     * @return exists Whether content is registered
     */
    function contentExists(string memory _sha256Hash) 
        public 
        view 
        returns (bool exists) 
    {
        return contentRegistry[_sha256Hash].exists;
    }
    
    /**
     * @dev Get content by index (for enumeration)
     * @param _index Index in the registry
     * @return sha256Hash Hash of the content at that index
     */
    function getContentByIndex(uint256 _index) 
        public 
        view 
        returns (string memory sha256Hash) 
    {
        require(_index < allContentHashes.length, "Index out of bounds");
        return allContentHashes[_index];
    }
}